import type { AppProps } from "next/app";
import React, { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import "../public/styles/App.css";
import "../public/styles/index.css";
import "../public/styles/FileViewer.css";
import "../public/styles/CustomQuery.css";
import { fetchUser, logoutUser, fetchAdminUsers } from "../utils/api";

interface User {
  email: string;
  role?: {
    name: string;
  };
}
interface AdminUser {
  email: string;
  role: {
    name: string;
  };
}

export default function MyApp({ Component, pageProps }: AppProps) {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [showUserContextMenu, setShowUserContextMenu] = useState(false);
  const [showDocumentsSubmenu, setShowDocumentsSubmenu] = useState(false); // State for Documents submenu
  const userContextMenuRef = useRef<HTMLDivElement>(null);
  const userCircleRef = useRef<HTMLDivElement>(null);
  const documentsMenuRef = useRef<HTMLDivElement>(null); // Ref for Documents menu item
  const documentsSubmenuRef = useRef<HTMLDivElement>(null); // Ref for Documents submenu
  const [isAdmin, setIsAdmin] = useState(false);
  const [adminUsers, setAdminUsers] = useState<User[]>([]);

  useEffect(() => {
    const getUserDetails = async () => {
      setLoading(true); // Start loading
      try {
        const userData = await fetchUser();
        setUser(userData);
        if (userData) {
          // Only fetch admin users if user is logged in
          const adminList = await fetchAdminUsers();
          setAdminUsers(adminList);

          const match = adminList.find(
            (adminUser: AdminUser) =>
              adminUser.email === userData?.email &&
              adminUser.role.name === "ADMIN"
          );
          setIsAdmin(!!match);
        } else {
          setIsAdmin(false); // Not admin if not logged in
        }
      } catch (error) {
        console.error("Error fetching user or admin users:", error);
        setIsAdmin(false);
      } finally {
        setLoading(false);
      }
    };
    getUserDetails();
  }, []); // Fetch user details only once on mount

  useEffect(() => {
    // Add click outside listener to close menus
    const handleClickOutside = (event: MouseEvent) => {
      // Close user context menu
      if (
        userContextMenuRef.current &&
        !userContextMenuRef.current.contains(event.target as Node) &&
        userCircleRef.current &&
        !userCircleRef.current.contains(event.target as Node)
      ) {
        setShowUserContextMenu(false);
      }
      // Close documents submenu
      if (
        documentsSubmenuRef.current &&
        !documentsSubmenuRef.current.contains(event.target as Node) &&
        documentsMenuRef.current &&
        !documentsMenuRef.current.contains(event.target as Node)
      ) {
        setShowDocumentsSubmenu(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []); // Add/remove listener only once

  // Close Documents submenu when route changes
  useEffect(() => {
    const handleRouteChange = () => {
      setShowDocumentsSubmenu(false);
    };
    router.events.on("routeChangeComplete", handleRouteChange);
    return () => {
      router.events.off("routeChangeComplete", handleRouteChange);
    };
  }, [router.events]);

  const isActive = (pathname: string | string[]) => {
    if (Array.isArray(pathname)) {
      return pathname.some((p) => router.pathname.startsWith(p));
    }
    return router.pathname === pathname;
  };

  const handleLogout = async () => {
    setShowUserContextMenu(false);
    try {
      await logoutUser();
    } catch (error) {
      console.error("Error during logout:", error);
    }
    window.location.href = "/api/auth/logout"; // Redirect to backend logout
  };

  const toggleUserContextMenu = () => {
    setShowUserContextMenu((prev) => !prev);
  };

  const toggleDocumentsSubmenu = (e: React.MouseEvent) => {
    e.preventDefault(); // Prevent default link behavior if any
    setShowDocumentsSubmenu((prev) => !prev);
  };

  const getUserInitials = () => {
    if (!user || !user.email) return "?";
    const emailName = user.email.split("@")[0];
    const nameParts = emailName.split(".");
    if (nameParts.length >= 2) {
      return (nameParts[0][0] + nameParts[1][0]).toUpperCase();
    } else {
      return emailName.substring(0, 2).toUpperCase();
    }
  };

  // Define paths for the Documents section
  const documentPaths = ["/file-viewer", "/files-upload"];

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-content">
          <h1>🔎 NISTA Scout</h1>
          <nav className="header-nav">
            {/* Summary Link */}
            <Link href="/" passHref legacyBehavior>
              <a className={`nav-link ${isActive("/") ? "active" : ""}`}>
                Summary
              </a>
            </Link>

            {/* Results Link */}
            <Link href="/results" passHref legacyBehavior>
              <a className={`nav-link ${isActive("/results") ? "active" : ""}`}>
                Results
              </a>
            </Link>

            {/* Documents Dropdown */}
            <div className="nav-item-container" ref={documentsMenuRef}>
              <a
                href="#" // Use href="#" or similar for non-navigating link
                onClick={toggleDocumentsSubmenu}
                className={`nav-link ${
                  isActive(documentPaths) ? "active" : ""
                }`}
              >
                Documents {showDocumentsSubmenu ? "▲" : "▼"}
              </a>
              {showDocumentsSubmenu && (
                <div className="submenu" ref={documentsSubmenuRef}>
                  <Link href="/file-viewer" passHref legacyBehavior>
                    <a
                      className={`submenu-link ${
                        isActive("/file-viewer") ? "active" : ""
                      }`}
                    >
                      Viewer
                    </a>
                  </Link>
                  {/* Conditionally render File Browser link based on isAdmin status */}
                  {isAdmin && (
                    <Link href="/files-upload" passHref legacyBehavior>
                      <a
                        className={`submenu-link ${
                          isActive("/files-upload") ? "active" : ""
                        }`}
                      >
                        File Upload (Admin)
                      </a>
                    </Link>
                  )}
                </div>
              )}
            </div>

            {/* Custom Query Link */}
            <Link href="/custom-query" passHref legacyBehavior>
              <a
                className={`nav-link ${
                  isActive("/custom-query") ? "active" : ""
                }`}
              >
                Custom Query
              </a>
            </Link>

            {/* Admin Link */}
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
                    onClick={toggleUserContextMenu}
                    title={user.email}
                  >
                    {getUserInitials()}
                  </div>
                  {showUserContextMenu && (
                    <div ref={userContextMenuRef} className="user-context-menu">
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
                    onClick={toggleUserContextMenu}
                  >
                    ?
                  </div>
                  {showUserContextMenu && (
                    <div ref={userContextMenuRef} className="user-context-menu">
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
