"use client"; // This is a client component

import React, { useEffect } from "react";
import Link from "next/link";
import { signOut } from "next-auth/react";

const SignedOut: React.FC = () => {
  return (
    <div style={{ textAlign: "center", marginTop: "50px" }}>
      <h1>You have successfully signed out</h1>
      <p>
        <Link href="/auth/signin" passHref legacyBehavior>
          <a>Sign in again</a>
        </Link>
      </p>
    </div>
  );
};

export default SignedOut;
