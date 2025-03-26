import type { AppProps } from "next/app";
import React, { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import "../public/styles/App.css";
import "../public/styles/index.css";
import "../public/styles/FileViewer.css";
import { fetchUser, logoutUser, fetchAdminUsers } from "../utils/api";

interface User {
  email: string;
  role: string;
}
interface AdminUser {
  email: string;
  role: string;
}

export default function MyApp({ Component, pageProps }: AppProps) {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [showContextMenu, setShowContextMenu] = useState(false);
  const contextMenuRef = useRef<HTMLDivElement>(null);
  const userCircleRef = useRef<HTMLDivElement>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [adminUsers, setAdminUsers] = useState<User[]>([]);

  useEffect(() => {
    const getUserDetails = async () => {
      try {
        const userData = await fetchUser();
        setUser(userData);
        const adminList = await fetchAdminUsers();
        setAdminUsers(adminList);

        const match = adminList.find(
          (adminUser: AdminUser) =>
            adminUser.email === userData?.email && adminUser.role === "admin"
        );
        setIsAdmin(!!match);
        
        console.log("setIsAdmin:", !!match);
      } catch (error) {
        console.error("Error fetching user or admin users:", error);
      } finally {
        setLoading(false);
      }
    };

    getUserDetails();

    // Add click outside listener to close context menu
    const handleClickOutside = (event: MouseEvent) => {
      if (
        contextMenuRef.current &&
        !contextMenuRef.current.contains(event.target as Node) &&
        userCircleRef.current &&
        !userCircleRef.current.contains(event.target as Node)
      ) {
        setShowContextMenu(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const isActive = (pathname: string) => router.pathname === pathname;

  const handleLogout = async () => {
    // Close context menu
    setShowContextMenu(false);

    // Clear cookies server-side
    try {
      await logoutUser();
    } catch (error) {
      console.error("Error during logout:", error);
      // Handle logout error (e.g., display a message)
    }

    // Redirect to Cognito logout
    window.location.href = "/api/auth/logout";
  };

  const toggleContextMenu = () => {
    setShowContextMenu((prev) => !prev);
  };

  // Function to get user initials
  const getUserInitials = () => {
    if (!user || !user.email) return "?";

    // Extract name from email (assuming format: firstname.lastname@domain.com)
    const emailName = user.email.split("@")[0];
    const nameParts = emailName.split(".");

    if (nameParts.length >= 2) {
      return (nameParts[0][0] + nameParts[1][0]).toUpperCase();
    } else {
      // If email doesn't contain a period, use first two letters
      return emailName.substring(0, 2).toUpperCase();
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-content">
          <h1>🔎 IPA Scout</h1>
          <nav className="header-nav">
            <Link href="/" passHref legacyBehavior>
              <a className={`nav-link ${isActive("/") ? "active" : ""}`}>
                Summary
              </a>
            </Link>
            <Link href="/results" passHref legacyBehavior>
              <a className={`nav-link ${isActive("/results") ? "active" : ""}`}>
                Results
              </a>
            </Link>
            <Link href="/file-viewer/" passHref legacyBehavior>
              <a
                className={`nav-link ${
                  isActive("/file-viewer") ? "active" : ""
                }`}
              >
                File Viewer
              </a>
            </Link>
            {isAdmin && (
              <Link href="/admin" passHref legacyBehavior>
                <a className={`nav-link ${isActive("/admin") ? "active" : ""}`}>
                  Admin
                </a>
              </Link>
            )}
          </nav>
          <div className="user-section">
            {!loading &&
              (user ? (
                <div className="user-profile-container">
                  <div
                    ref={userCircleRef}
                    className="user-initials-circle"
                    onClick={toggleContextMenu}
                    title={user.email}
                  >
                    {getUserInitials()}
                  </div>
                  {showContextMenu && (
                    <div ref={contextMenuRef} className="user-context-menu">
                      <div className="user-email">{user.email}</div>
                      <button
                        onClick={handleLogout}
                        className="context-menu-button"
                      >
                        Logout
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <div className="user-profile-container">
                  <div
                    ref={userCircleRef}
                    className="user-initials-circle"
                    onClick={toggleContextMenu}
                  >
                    ?
                  </div>
                  {showContextMenu && (
                    <div ref={contextMenuRef} className="user-context-menu">
                      <Link href="/api/auth/login" passHref legacyBehavior>
                        <a className="context-menu-button">Login</a>
                      </Link>
                    </div>
                  )}
                </div>
              ))}
          </div>
        </div>
      </header>
      <main className="main-content">
        <Component {...pageProps} adminUsers={adminUsers} />
      </main>
      <footer className="App-footer">
        <div className="footer-content">
          <Link href="/privacy-policy" passHref legacyBehavior>
            <a>Privacy Policy</a>
          </Link>
          <span className="footer-separator">|</span>
          <a href="mailto:i-dot-ai-enquiries@cabinetoffice.gov.uk">Support</a>
        </div>
      </footer>
    </div>
  );
}
