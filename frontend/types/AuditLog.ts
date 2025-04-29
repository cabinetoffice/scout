export interface AuditLog {
    id: string;
    timestamp: string;
    user_id: string;
    action_type: string;
    details: Record<string, any>;
    ip_address: string;
    user_agent: string;
  }