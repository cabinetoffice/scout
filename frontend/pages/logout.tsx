import { useEffect } from "react";
import { useRouter } from "next/router";
import Image from "next/image";
import Head from "next/head";
import { logoutUser } from "@/utils/api";

export default function Logout() {
  const router = useRouter();

  useEffect(() => {
    const clearCookiesAndRedirect = async () => {
      // Clear all cookies client-side
      const cookiesToClear = [
        "AWSALB",
        "AWSALBAuthNonce",
        "AWSALBCORS",
        "AWSALBTG",
        "AWSALBTGCORS",
        "AWSELBAuthSessionCookie-0",
        "AWSELBAuthSessionCookie-1",
      ];

      // Common domains to try
      const domains = process.env.LOGOUT_DOMAINS
        ? process.env.LOGOUT_DOMAINS.split(",")
        : [];

      // Common paths to try
      const paths = ["/", "/file-viewer", ""];

      // Clear each cookie with different domain/path combinations
      cookiesToClear.forEach((cookieName) => {
        domains.forEach((domain) => {
          paths.forEach((path) => {
            document.cookie = `${cookieName}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; ${
              domain ? `domain=${domain}; ` : ""
            }path=${path}; secure; samesite=strict`;
          });
        });
      });

      // Also make a request to the API route to clear cookies server-side
      try {
        await logoutUser();
      } catch (error) {
        console.error("Error during logout:", error);
        // Handle error here, e.g., show an error message to the user
      }

      // Redirect to login page after 10 seconds
      const redirectTimer = setTimeout(() => {
        router.push("/");
      }, 10000);

      return () => clearTimeout(redirectTimer);
    };

    clearCookiesAndRedirect();
  }, [router]);

  return (
    <>
      <Head>
        <title>Logged Out - IPA Scout</title>
        <meta
          name="description"
          content="You have been logged out of IPA Scout"
        />
      </Head>

      <div style={{ textAlign: "center", marginTop: "20vh" }}>
        <h1>You have been logged out</h1>
        <p>Please close this tab or your browser for security reasons.</p>
        <p>Redirecting to login...</p>
      </div>
    </>
  );
}
