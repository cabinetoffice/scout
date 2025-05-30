import React, { useEffect, useState } from "react";
import { Chip } from "@mui/material";
import { AgGridReact } from "ag-grid-react";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import { ColDef, ICellRendererParams } from "ag-grid-community";
import AssessmentIcon from "@mui/icons-material/Assessment";
import { useRouter } from "next/router";

import {
  addUserToProject,
  removeUserFromProject,
  fetchItems,
  fetchAdminUsers,
  fetchProjectsAsAdmin,
  createUser,
  updateUser,
} from "@/utils/api";

const roles = [
  { name: "ADMIN", color: "#f54242" }, // Red for admin
  { name: "UPLOADER", color: "#2196f3" }, // Blue for uploader
  { name: "USER", color: "#4caf50" }, // Green for regular users
];

interface Project {
  id: string;
  name: string;
  created_datetime?: string;
  updated_datetime?: string;
  results_summary?: any;
}
interface Role {
  id: string;
  name: string;
  description?: string;
  created_datetime?: string;
  updated_datetime?: string;
}
interface User {
  id: string;
  email: string;
  role: Role;
  projects?: Project[];
}

export default function AdminPage({ refreshProjectInfo }: { refreshProjectInfo: () => void }) {
  const router = useRouter();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const RoleSelector = ({
    selectedRole,
    onRoleSelect,
  }: {
    selectedRole: Role;
    onRoleSelect: (roleName: string) => void;
  }) => (
    <div style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
      {roles.map((role) => (
        <Chip
          key={role.name}
          label={role.name}
          onClick={() => onRoleSelect(role.name)}
          variant={selectedRole?.name === role.name ? "filled" : "outlined"}
          style={{
            backgroundColor:
              selectedRole?.name === role.name ? role.color : "transparent",
            color: selectedRole?.name === role.name ? "white" : "inherit",
            cursor: "pointer",
          }}
        />
      ))}
    </div>
  );
  const [formUser, setFormUser] = useState<User>({
    id: "",
    email: "",
    role: { id: "", name: "" },
    projects: [],
  });
  const [allProjects, setAllProjects] = useState<Project[]>([]);

  const fetchUsers = async () => {
    try {
      const adminUsers = await fetchAdminUsers();
      setUsers(adminUsers);
    } catch (err) {
      console.error("Failed to fetch users", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  useEffect(() => {
    const fetchAllProjects = async () => {
      try {
        const projects = await fetchProjectsAsAdmin();
        setAllProjects(projects);
      } catch (error) {
        console.error("Error fetching all projects:", error);
      }
    };
    fetchAllProjects();
  }, []);

  const handleSave = async () => {
    if ((formUser.projects?.length || 0) > 1) {
      window.alert("Scout can only assign 1 project per user at this time");
      return;
    }

    // Validate role is selected
    if (!formUser.role?.name) {
      window.alert("Please select a role for the user");
      return;
    }

    if (editingIndex === null) {
      try {
        const newUser = await createUser({
          action: "create",
          emails: [formUser.email],
        });
        console.log("New user created:", newUser);

        // Fetch the updated user list to get the new user's ID
        await fetchUsers();
        const createdUser = users.find((u) => u.email === formUser.email);

        if (!createdUser) {
          console.error("User not found for email:", formUser.email);
          return;
        }

        // Always update role for new users since they might not have one initially
        await updateUser({
          user_id: createdUser.id,
          role: formUser.role.name,
        });

        fetchUsers();
      } catch (error) {
        console.error("Error creating new user:", error);
      }
    } else {
      try {
        const currentUser = users[editingIndex];

        // Update role if changed or if current user has no role
        if (!currentUser.role?.name || currentUser.role.name !== formUser.role.name) {
          await updateUser({
            user_id: currentUser.id,
            role: formUser.role.name,
          });
        }

        const user = users[editingIndex];
        const userProjects = user.projects || [];
        const formProjects = formUser.projects || [];

        // Handle project changes
        const projectsToRemove = userProjects.filter(
          (p) => !formProjects.some((fp) => fp.id === p.id)
        );
        const projectsToAdd = formProjects.filter(
          (fp) => !userProjects.some((p) => p.id === fp.id)
        );

        for (const project of projectsToRemove) {
          try {
            await removeUserFromProject({
              user_id: user.id,
              project_id: project.id,
            });
            console.log(`Removed user ${user.id} from project ${project.id}`);
          } catch (error) {
            console.error(
              `Error removing user ${user.id} from project ${project.id}:`,
              error
            );
          }
        }

        for (const project of projectsToAdd) {
          try {
            await addUserToProject({
              user_id: user.id,
              project_id: project.id,
            });
            console.log(`Added user ${user.id} to project ${project.id}`);
          } catch (error) {
            console.error(
              `Error adding user ${user.id} to project ${project.id}:`,
              error
            );
          }
        }

        // Refresh the users list
        fetchUsers();
      } catch (error) {
        console.error("Error updating user:", error);
      }
    }

    if (typeof refreshProjectInfo === "function") {
      await refreshProjectInfo();
    }

    setShowForm(false);
    setEditingIndex(null);
    setFormUser({
      id: "",
      email: "",
      role: { id: "", name: "" },
      projects: [],
    });
  };

  const handleEdit = (index: number) => {
    const u = users[index];
    setEditingIndex(index);
    setFormUser({
      id: u.id,
      email: u.email,
      role: u.role,
      projects: u.projects || [],
    });
    setShowForm(true);
  };

  const handleDelete = async (index: number) => {
    const userToDelete = users[index];
    if (window.confirm(`Delete user "${userToDelete.email}"?`)) {
      try {
        const deleteUser = await createUser({
          action: "delete",
          emails: [userToDelete.email],
        });
        console.log("User Delete:", deleteUser);

        const updated = [...users];
        updated.splice(index, 1);
        setUsers(updated);
        console.log(`User ${userToDelete.email} deleted successfully.`);
      } catch (error) {
        console.error(`Error deleting user ${userToDelete.email}:`, error);
      }
    }
  };

  const projectsFormatter = (params: any) => {
    return params.value && params.value.length > 0 ? (
      <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
        {params.value.map((p: Project) => (
          <Chip
            key={p.id}
            label={p.name}
            variant="outlined"
            style={{ backgroundColor: "lightgrey" }}
          />
        ))}
      </div>
    ) : (
      <span style={{ fontStyle: "italic", color: "gray" }}>No projects</span>
    );
  };

  const columnDefs: ColDef[] = [
    {
      headerName: "Email",
      field: "email",
      wrapText: true,
      autoHeight: true,
      flex: 2,
      cellStyle: { textAlign: "center" },
      headerClass: "center-header",
    },
    {
      headerName: "Role",
      field: "role",
      wrapText: true,
      autoHeight: true,
      flex: 1,
      cellStyle: { textAlign: "center" },
      headerClass: "center-header",
      cellRenderer: (params: ICellRendererParams) => {
        const roleConfig = roles.find((r) => r.name === params.value?.name);
        return roleConfig ? (
          <Chip
            label={roleConfig.name}
            style={{
              backgroundColor: roleConfig.color,
              color: "white",
            }}
          />
        ) : (
          params.value?.name || "No role"
        );
      },
      valueFormatter: (params) => params.value?.name || "No role",
    },
    {
      headerName: "Projects",
      field: "projects",
      wrapText: true,
      autoHeight: true,
      flex: 3,
      cellRenderer: projectsFormatter,
      cellStyle: { textAlign: "center" },
      headerClass: "center-header",
      valueFormatter: (params) =>
        Array.isArray(params.value)
          ? params.value.map((p: Project) => p.name).join(", ")
          : params.value?.name || "No projects",
    },
    {
      headerName: "Actions",
      field: "id",
      wrapText: true,
      autoHeight: true,
      flex: 1,
      cellStyle: { textAlign: "center" },
      headerClass: "center-header",
      cellRenderer: (params: ICellRendererParams) => (
        <div>
          <button
            onClick={() =>
              handleEdit(users.findIndex((u) => u.id === params.data.id))
            }
            style={actionButtonStyle}
          >
            Edit
          </button>
          <button
            onClick={() =>
              handleDelete(users.findIndex((u) => u.id === params.data.id))
            }
            style={{ ...actionButtonStyle, color: "red" }}
          >
            Delete
          </button>
        </div>
      ),
    },
  ];

  const ProjectSelector = ({
    selectedProject,
    allProjects,
    onProjectSelect,
  }: {
    selectedProject: Project | null;
    allProjects: Project[];
    onProjectSelect: (project: Project | null) => void;
  }) => (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginBottom: "16px" }}>
      {allProjects.map((project) => (
        <Chip
          key={project.id}
          label={project.name}
          onClick={() => {
            // Toggle between selecting this project or none
            if (selectedProject?.id === project.id) {
              onProjectSelect(null);
            } else {
              onProjectSelect(project);
            }
          }}
          variant={selectedProject?.id === project.id ? "filled" : "outlined"}
          style={{
            backgroundColor: selectedProject?.id === project.id ? "lightblue" : "lightgrey",
            cursor: "pointer",
          }}
        />
      ))}
      {allProjects.length > 0 && (
        <Chip
          label="None"
          onClick={() => onProjectSelect(null)}
          variant={selectedProject === null ? "filled" : "outlined"}
          style={{
            backgroundColor: selectedProject === null ? "#f5f5f5" : "transparent",
            border: "1px dashed #aaa",
            cursor: "pointer",
          }}
        />
      )}
    </div>
  );

  const handleProjectSelect = (project: Project | null) => {
    setFormUser((prev) => ({
      ...prev,
      projects: project ? [project] : [],
    }));
  };

  const menuItems = [
    {
      text: "Audit Logs",
      icon: <AssessmentIcon />,
      onClick: () => router.push("/audit-logs"),
    },
  ];

  return (
    <div style={{ width: "100%", height: "100vh" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "20px",
        }}
      >
        <h2 style={{ fontSize: "1.5rem", fontWeight: "bold", margin: 0 }}>
          User Management
        </h2>
        <div style={{ display: "flex", gap: "10px" }}>
          <button
            onClick={() => {
              setEditingIndex(null);
              setFormUser({
                id: "",
                email: "",
                role: { id: "", name: "" },
                projects: [],
              });
              setShowForm(true);
            }}
            style={addButtonStyles}
          >
            Add New User
          </button>
          <button
            onClick={() => router.push("/audit-logs")}
            style={{ ...addButtonStyles, backgroundColor: "#2196F3" }}
          >
            View Audit Logs
          </button>
        </div>
      </div>
      {users.length === 0 ? (
        <p style={{ color: "gray", textAlign: "center" }}>No users found.</p>
      ) : (
        <div
          className="ag-theme-alpine"
          style={{ height: "calc(100% - 160px)", width: "100%", margin: "0" }}
        >
          <AgGridReact
            rowData={users}
            columnDefs={columnDefs}
            defaultColDef={{
              wrapText: true,
              autoHeight: true,
            }}
          />
        </div>
      )}

      {showForm && (
        <div className="modal-overlay" style={modalOverlayStyle}>
          <div className="modal-content" style={modalContentStyle}>
            <h3
              style={{
                fontSize: "1.2rem",
                fontWeight: "bold",
                marginBottom: "15px",
                textAlign: "center",
              }}
            >
              {editingIndex === null ? "Add New User" : "Edit User"}
            </h3>

            <label style={formLabelStyle}>Email</label>
            <input
              type="text"
              value={formUser.email}
              onChange={(e) =>
                setFormUser((prev) => ({ ...prev, email: e.target.value }))
              }
              style={formInputStyle}
            />

            <label style={formLabelStyle}>Role</label>
            <RoleSelector
              selectedRole={formUser.role}
              onRoleSelect={(roleName) =>
                setFormUser((prev) => ({
                  ...prev,
                  role: { ...prev.role, name: roleName },
                }))
              }
            />

            <label style={formLabelStyle}>Project</label>  {/* Changed from "Projects" to "Project" */}
            <ProjectSelector
              selectedProject={formUser.projects && formUser.projects.length > 0 ? formUser.projects[0] : null}
              allProjects={allProjects}
              onProjectSelect={handleProjectSelect}
            />

            <div
              style={{
                display: "flex",
                justifyContent: "center",
                gap: "10px",
                marginTop: "20px",
              }}
            >
              <button onClick={handleSave} style={saveButtonStyle}>
                Save
              </button>
              <button
                onClick={() => {
                  setShowForm(false);
                  setEditingIndex(null);
                  setFormUser({
                    id: "",
                    email: "",
                    role: { id: "", name: "" },
                    projects: [],
                  });
                }}
                style={cancelButtonStyle}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
      <div
        style={{
          marginTop: "20px",
          textAlign: "center",
          position: "relative",
          bottom: 0,
          width: "100%",
        }}
      ></div>
    </div>
  );
}

// Styles
const actionButtonStyle: React.CSSProperties = {
  color: "blue",
  textDecoration: "underline",
  background: "none",
  border: "none",
  cursor: "pointer",
  marginRight: "10px",
};

const addButtonStyles: React.CSSProperties = {
  backgroundColor: "#4CAF50",
  color: "white",
  padding: "10px 15px",
  borderRadius: "5px",
  border: "none",
  cursor: "pointer",
};

const modalOverlayStyle: React.CSSProperties = {
  position: "fixed",
  top: 0,
  left: 0,
  width: "100%",
  height: "100%",
  backgroundColor: "rgba(0, 0, 0, 0.4)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
};

const modalContentStyle: React.CSSProperties = {
  backgroundColor: "white",
  padding: "20px",
  borderRadius: "10px",
  width: "90%",
  maxWidth: "500px",
};

const formLabelStyle: React.CSSProperties = {
  display: "block",
  marginBottom: "5px",
  textAlign: "left",
};

const formInputStyle: React.CSSProperties = {
  width: "100%",
  border: "1px solid #ddd",
  padding: "8px",
  borderRadius: "5px",
  marginBottom: "15px",
};

const saveButtonStyle: React.CSSProperties = {
  backgroundColor: "#d4708e",
  color: "white",
  padding: "10px 15px",
  borderRadius: "5px",
  border: "none",
  cursor: "pointer",
};

const cancelButtonStyle: React.CSSProperties = {
  backgroundColor: "#6c757d",
  color: "white",
  padding: "10px 15px",
  borderRadius: "5px",
  border: "none",
  cursor: "pointer",
};
