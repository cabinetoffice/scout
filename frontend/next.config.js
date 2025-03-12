/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  //   redirects: async () => {
  //     debugger;
  //     console.log(
  //       "======",
  //       `${process.env.NEXT_PUBLIC_COGNITO_AUTH_DOMAIN}/logout?client_id=${
  //         process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID
  //       }&logout_uri=${encodeURIComponent(
  //         "http://localhost:3000/signed-out"
  //       )}&response_type=code&scope=email+openid+phone&redirect_uri=${encodeURIComponent(
  //         `${process.env.NEXTAUTH_URL}/api/auth/cognito`
  //       )}`
  //     );
  //     return [
  //       {
  //         source: "/api/sso/logout",
  //         destination: `${
  //           process.env.NEXT_PUBLIC_COGNITO_AUTH_DOMAIN
  //         }/logout?client_id=${
  //           process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID
  //         }&logout_uri=${encodeURIComponent(
  //           "http://localhost:3000/signed-out"
  //         )}&response_type=code&scope=email+openid+phone&redirect_uri=${encodeURIComponent(
  //           `${process.env.NEXTAUTH_URL}/api/auth/cognito`
  //         )}`,
  //         permanent: false,
  //       },
  //     ];
  //   },
};

module.exports = nextConfig;
