import { SummaryData } from "@/types/SummaryData";

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

export const fetchFilebyKey = async (
  key: string
): Promise<{ url: string; fileType: string }> => {
  const response = await fetch(`/api/get_items_by_key/${key}`);
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

export const fetchUserRole = async () => {
  try {
    const response = await fetch("/api/user/role");
    if (!response.ok) {
      if (response.status === 401) {
        return null;
      }
      throw new Error("Failed to fetch user role");
    }
    return await response.json();
  } catch (error) {
    console.error("Error fetching user role:", error);
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
export const submitQuery = async (query: string, chat_session_id?: string, model_id?: string): Promise<any> => {
  const response = await fetch(`/api/custom-query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query, chat_session_id, model_id }),
  });

  if (!response.ok) {
    throw new Error("Failed to submit query");
  }

  return response.json();
};

export const fetchLLMModels = async (): Promise<any> => {
  const response = await fetch(`/api/llm/models`);
  if (!response.ok) throw new Error("Failed to fetch LLM models");
  return response.json();
};

  export const fetchFilesAsAdmin = async () => {
    try {
        const response = await fetch('/api/admin/files');
        if (!response.ok) {
        if (response.status === 401) {
            // User is not authenticated
            return null;
        }
        throw new Error('Failed to fetch admin files');
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching admin files:', error);
        return null;
    }
    };

    export const uploadFilesToS3 = async (formData: FormData) => {
      const res = await fetch("/api/admin/s3_upload", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("Upload failed");
    };

    export const deleteFileFromS3 = async (key: string) => {
      const res = await fetch(`/api/admin/s3_delete?key=${encodeURIComponent(key)}`);
      if (!res.ok) throw new Error("Failed to delete file");
    };

    export const getSignedFileUrl = async (key: string): Promise<string> => {
      const res = await fetch(`/api/admin/s3_signed_url?key=${encodeURIComponent(key)}`);
      if (!res.ok) throw new Error("Failed to get signed URL");
      const data = await res.json();
      return data.url;
    };

interface UpdateUserRequest {
    user_id: string;
    role: string;
}

export const updateUser = async (updateUserRequest: UpdateUserRequest): Promise<{ message: string }> => {
    const response = await fetch(`/api/admin/update_user`, {
        method: 'POST',
        body: JSON.stringify(updateUserRequest),
    });
    if (!response.ok) {
        console.error(`Error updating user ${updateUserRequest.user_id}:`);
        throw new Error('Failed to update user');
    }
    return response.json();
};

export async function fetchSummaryData(): Promise<SummaryData> {
  const res = await fetch(`/api/summary`);
  if (!res.ok) {
    throw new Error("Failed to fetch summary data");
  }
  return res.json();
}

export const fetchChatHistory = async (sessionId?: string) => {
  try {
    const url = sessionId 
      ? `/api/chat-history?session_id=${sessionId}`
      : '/api/chat-history';
      
    const response = await fetch(url, {
      method: 'GET',
      credentials: 'include',
    });
    
    if (!response.ok) {
      if (response.status === 401) {
        // User is not authenticated
        return null;
      }
      throw new Error('Failed to fetch chat history');
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching chat history:', error);
    return null;
  }
};

export const fetchChatSessions = async () => {
  try {
    const response = await fetch('/api/chat-sessions', {
      method: 'GET',
      credentials: 'include',
    });
    
    if (!response.ok) {
      if (response.status === 401) {
        return null;
      }
      throw new Error('Failed to fetch chat sessions');
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching chat sessions:', error);
    return null;
  }
};

export const createChatSession = async (title: string, sessionId?: string) => {
  try {
    const response = await fetch('/api/chat-sessions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ title, id: sessionId }),
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error('Failed to create chat session');
    }
    return await response.json();
  } catch (error) {
    console.error('Error creating chat session:', error);
    throw error;
  }
};

export const updateChatSession = async (sessionId: string, title: string) => {
  try {
    const response = await fetch(`/api/chat-sessions/${sessionId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ title }),
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error('Failed to update chat session');
    }
    return await response.json();
  } catch (error) {
    console.error('Error updating chat session:', error);
    throw error;
  }
};

export const deleteChatSession = async (sessionId: string) => {
  try {
    const response = await fetch(`/api/chat-sessions/${sessionId}`, {
      method: 'DELETE',
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error('Failed to delete chat session');
    }
    return await response.json();
  } catch (error) {
    console.error('Error deleting chat session:', error);
    throw error;
  }
};

export const fetchTopReferencedDocuments = async (limit: number = 10) => {
  try {
    const response = await fetch(`/api/top-referenced-documents?limit=${limit}`);
    if (!response.ok) {
      throw new Error('Failed to fetch top referenced documents');
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching top referenced documents:', error);
    throw error;
  }
};