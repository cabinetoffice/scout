import React, { useEffect, useState } from "react";
import { Chip } from "@mui/material";
import { AgGridReact } from "ag-grid-react";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import { ColDef, ICellRendererParams } from "ag-grid-community";

import {
  addUserToProject,
  removeUserFromProject,
  fetchItems,
  fetchAdminUsers,
  fetchProjectsAsAdmin,
} from "@/utils/api";

interface Project {
  id: string;
  name: string;
  created_datetime?: string;
  updated_datetime?: string;
  results_summary?: any;
}

interface User {
  id: string;
  email: string;
  role: string;
  projects?: Project[];
}

// export default function AdminPage({ adminUsers }: { adminUsers: User[] }) {
export default function AdminPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [formUser, setFormUser] = useState<User>({
    id: "",
    email: "",
    role: "",
    projects: [],
  });
  const [allProjects, setAllProjects] = useState<Project[]>([]);

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        //console.log("passed in AdminUsers:", adminUsers);
        const adminUsers = await fetchAdminUsers();
        setUsers(adminUsers);
      } catch (err) {
        console.error("Failed to fetch users", err);
      } finally {
        setLoading(false);
      }
    };
    fetchUsers();
  }, []);

  useEffect(() => {
    const fetchAllProjects = async () => {
      try {
        // const projects = await fetchItems("project");
        const projects = await fetchProjectsAsAdmin();
        console.log("All projects:", projects);
        setAllProjects(projects);
      } catch (error) {
        console.error("Error fetching all projects:", error);
      }
    };
    fetchAllProjects();
  }, []);

  const handleSave = async () => {
    if (editingIndex === null) {
      // Handle adding a new user (not implemented in this example)
      console.log("Adding new user not implemented");
    } else {
      const updatedUser = { ...formUser };
      const updated = [...users];
      updated[editingIndex] = updatedUser;
      setUsers(updated);

      // Update projects for the user
      const user = users[editingIndex];
      const userProjects = user.projects || [];
      const formProjects = formUser.projects || [];

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
          // Handle error appropriately (e.g., show a notification to the user)
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
          // Handle error appropriately (e.g., show a notification to the user)
        }
      }
    }

    setShowForm(false);
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

  const handleDelete = (index: number) => {
    if (window.confirm(`Delete user "${users[index].email}"?`)) {
      const updated = [...users];
      updated.splice(index, 1);
      setUsers(updated);
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

  const handleProjectToggle = (project: Project) => {
    setFormUser((prev) => {
      const isProjectSelected = prev.projects?.some((p) => p.id === project.id);
      if (isProjectSelected) {
        return {
          ...prev,
          projects: prev.projects?.filter((p) => p.id !== project.id),
        };
      } else {
        return {
          ...prev,
          projects: [...(prev.projects || []), project],
        };
      }
    });
  };

  return (
    <div style={{ width: "100%", height: "100vh" }}>
      <h2
        style={{
          fontSize: "1.5rem",
          fontWeight: "bold",
          marginTop: "2px",
          marginLeft: "20px",
          marginBottom: "20px",
          textAlign: "left",
        }}
      >
        <button
          onClick={() => {
            setEditingIndex(null);
            setFormUser({ id: "", email: "", role: "", projects: [] });
            setShowForm(true);
          }}
          style={addButtonStyles}
        >
          Add New User
        </button>
      </h2>
      {users.length === 0 ? (
        <p style={{ color: "gray", textAlign: "center" }}>No users found.</p>
      ) : (
        <div
          className="ag-theme-alpine"
          style={{ height: "calc(100% - 160px)", width: "100%", margin: "0" }} // Removed padding from table container
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
            <input
              type="text"
              value={formUser.role}
              onChange={(e) =>
                setFormUser((prev) => ({ ...prev, role: e.target.value }))
              }
              style={formInputStyle}
            />

            <label style={formLabelStyle}>Projects</label>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
              {allProjects.map((project) => (
                <Chip
                  key={project.id}
                  label={project.name}
                  variant={
                    formUser.projects?.some((p) => p.id === project.id)
                      ? "filled"
                      : "outlined"
                  }
                  onClick={() => handleProjectToggle(project)}
                  style={{
                    backgroundColor: formUser.projects?.some(
                      (p) => p.id === project.id
                    )
                      ? "lightblue"
                      : "lightgrey",
                    cursor: "pointer",
                  }}
                />
              ))}
            </div>

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
                onClick={() => setShowForm(false)}
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
  backgroundColor: "#007bff",
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
