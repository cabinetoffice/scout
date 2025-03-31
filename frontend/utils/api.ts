interface Filters {
  model: string;
  filters: Record<string, any>;
}

export async function fetchAPIInfo() {
  const res = await fetch(`/api/info`);
  if (!res.ok) {
    throw new Error("Failed to fetch data");
  }
  const data = await res.json();
  return data.backend;
}

export const fetchUser = async () => {
  try {
    const response = await fetch("/api/auth/user");
    if (!response.ok) {
      if (response.status === 401) {
        // User is not authenticated
        return null;
      }
      throw new Error("Failed to fetch user data");
    }
    return await response.json();
  } catch (error) {
    console.error("Error fetching user data:", error);
    return null;
  }
};

export const fetchReadItemsByAttribute = async (
  filters: Filters
): Promise<any> => {
  const response = await fetch(`/api/read_items_by_attribute`, {
    method: "POST",
    body: JSON.stringify(filters),
  });
  if (!response.ok) throw new Error("Failed to read items by attribute");
  return response.json();
};

export const fetchItems = async (
  table: string,
  uuid?: string
): Promise<any> => {
  let url = `/api/item/${table}`;
  if (uuid) url += `?uuid=${encodeURIComponent(uuid)}`;
  const response = await fetch(url);
  if (!response.ok) throw new Error("Failed to fetch items");
  return response.json();
};

export const fetchRelatedItems = async (
  uuid: string,
  model1: string,
  model2: string,
  limit_to_user: boolean
): Promise<any> => {
  const response = await fetch(
    `/api/related/${uuid}/${model1}/${model2}?limit_to_user=${limit_to_user}`
  );
  if (!response.ok) throw new Error("Failed to fetch related items");
  return response.json();
};

export const fetchFile = async (
  uuid: string
): Promise<{ url: string; fileType: string }> => {
  const response = await fetch(`/api/get_items/${uuid}`);
  if (!response.ok) throw new Error("Failed to fetch file");

  const fileType =
    response.headers.get("Content-Type") || "application/octet-stream";

  // Create a new ReadableStream from the response body
  const reader = response.body?.getReader();
  const stream = new ReadableStream({
    start(controller) {
      return pump();
      function pump(): Promise<void> {
        return (
          reader?.read().then(({ done, value }) => {
            if (done) {
              controller.close();
              return;
            }
            controller.enqueue(value);
            return pump();
          }) || Promise.resolve()
        );
      }
    },
  });

  // Create a new response with the stream
  const newResponse = new Response(stream);

  // Get the blob from the new response
  const blob = await newResponse.blob();

  const pdf_blob = blob.slice(0, blob.size, "application/pdf");

  // Create a URL for the blob
  const url = URL.createObjectURL(pdf_blob);

  return { url, fileType };
};

interface RatingRequest {
  result_id: string;
  good_response: boolean;
}

export const rateResponse = async (
  ratingRequest: RatingRequest
): Promise<{ message: string }> => {
  const response = await fetch(`/api/rate`, {
    method: "POST",
    body: JSON.stringify(ratingRequest),
  });
  if (!response.ok) throw new Error("Failed to submit rating");
  return response.json();
};

export const logoutUser = async () => {
  const response = await fetch("/api/logout", {
    method: "POST",
  });
  if (!response.ok) throw new Error("Failed to logout");
};

export const fetchAdminUsers = async () => {
  try {
    const response = await fetch("/api/admin/users");
    if (!response.ok) {
      if (response.status === 401) {
        // User is not authenticated
        return null;
      }
      throw new Error("Failed to fetch admin users");
    }
    return await response.json();
  } catch (error) {
    console.error("Error fetching admin users:", error);
    return null;
}
};

export const fetchProjectsAsAdmin = async () => {
    try {
        const response = await fetch('/api/admin/projects');
        if (!response.ok) {
        if (response.status === 401) {
            // User is not authenticated
            return null;
        }
        throw new Error('Failed to fetch admin projects');
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching admin projects:', error);
        return null;
    }
    };

interface AssociateUserToProjectRequest {
    user_id: string;
    project_id: string;
}

export const addUserToProject = async (associateUserToProjectRequest: AssociateUserToProjectRequest): Promise<{ message: string }> => {
    const response = await fetch(`/api/add_user_to_project`, {
        method: 'POST',
        body: JSON.stringify(associateUserToProjectRequest),
    });
    if (!response.ok) {
        console.error(`Error adding user ${associateUserToProjectRequest.user_id} to project ${associateUserToProjectRequest.project_id}:`);
        throw new Error('Failed to add user to project');
    }
    return response.json();
};
export const removeUserFromProject = async (associateUserToProjectRequest: AssociateUserToProjectRequest): Promise<{ message: string }> => {
    const response = await fetch(`/api/remove_user_from_project`, {
        method: 'POST',
        body: JSON.stringify(associateUserToProjectRequest),
    });
    if (!response.ok) {
        console.error(`Error removing user ${associateUserToProjectRequest.user_id} from project ${associateUserToProjectRequest.project_id}:`);
        throw new Error('Failed to add user to project');
    }
    return response.json();
};

interface CreateUserRequest {
    action: 'create' | 'delete';
    emails: string[];
}

export const createUser = async (createUserRequest: CreateUserRequest): Promise<{ message: string }> => {
    const response = await fetch(`/api/auth/create_user`, {
        method: 'POST',
        body: JSON.stringify(createUserRequest),
    });
    if (!response.ok) {
        console.error(`Error creating user ${createUserRequest.emails}:`);
        throw new Error('Failed to create user');
    }
    return response.json();
};
export const submitQuery = async (query: string): Promise<any> => {
    const response = await fetch(`/api/custom-query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query }),
    });
  
    if (!response.ok) {
      throw new Error("Failed to submit query");
    }
  
    return response.json();
  };
