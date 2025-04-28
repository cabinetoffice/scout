/** @type {import('next').NextConfig} */
const nextConfig = {
    output: "standalone",
    transpilePackages: ['@mui/material', '@mui/system', '@mui/x-date-pickers', '@emotion/react', '@emotion/styled'],
}

module.exports = nextConfig
