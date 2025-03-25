import React from "react";

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

export default function AdminPage({ adminUsers }: { adminUsers: User[] }) {
  if (!adminUsers || adminUsers.length === 0) {
    return (
      <div className="content text-center">
        <p className="text-gray-600 text-lg">No users found.</p>
      </div>
    );
  }

  return (
    <div className="content">
      <div className="summary-card">
        <h2>Users and Projects List</h2>
        <table className="w-full">
          <thead
            style={{
              backgroundColor: "#f1f5f9",
              borderBottom: "2px solid #e0e0e0",
            }}
          >
            <tr>
              <th className="p-3 text-left text-sm font-semibold text-gray-600 uppercase tracking-wide">
                User
              </th>
              <th className="p-3 text-left text-sm font-semibold text-gray-600 uppercase tracking-wide">
                Role
              </th>
              <th className="p-3 text-left text-sm font-semibold text-gray-600 uppercase tracking-wide">
                Projects
              </th>
            </tr>
          </thead>
          <tbody>
            {adminUsers.map((user) => (
              <tr
                key={user.id}
                className="border-b hover:bg-gray-50 transition-colors"
              >
                <td className="p-3 flex items-center space-x-3">
                  <div className="user-initials-circle">
                    {user.email.charAt(0).toUpperCase()}
                  </div>
                  <span className="text-sm font-medium text-gray-900">
                    {user.email}
                  </span>
                </td>
                <td className="p-3 text-sm text-gray-700">
                  {user.role || (
                    <span className="italic text-gray-400">Not specified</span>
                  )}
                </td>
                <td className="p-3 text-sm text-gray-700">
                  {user.projects && user.projects.length > 0 ? (
                    <ul className="list-disc list-inside space-y-1">
                      {user.projects.map((project) => (
                        <li key={project.id}>{project.name}</li>
                      ))}
                    </ul>
                  ) : (
                    <span className="italic text-gray-400">No projects</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
