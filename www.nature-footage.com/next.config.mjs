/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    domains: [
      'prod-tl-emc-destination.s3.us-west-2.amazonaws.com',
      'project-one-thumbnail.s3.us-west-2.amazonaws.com',
      's3.us-west-2.amazonaws.com',
      'test-001-fashion.s3.eu-north-1.amazonaws.com'
    ],
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
    unoptimized: true,
  },
};

export default nextConfig;
