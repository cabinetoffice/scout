import { logOut } from "@/utils/api";
import { sign } from "crypto";
import { signOut, useSession } from "next-auth/react";

declare module "next-auth" {
  interface Session {
    refreshToken?: string;
  }
}

export default function LogoutButton() {
  const { data } = useSession();
  const handleLogout = async () => {
    data && (await logOut(data.refreshToken as string));
  };

  return (
    <a className="nav-link" onClick={handleLogout}>
      Logout
    </a>
  );
}
