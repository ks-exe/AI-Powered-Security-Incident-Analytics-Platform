module.exports = {
  dbType: 'duckdb',

  driverFactory: () => ({
    type: 'duckdb',
    database: process.env.CUBEJS_DB_DUCKDB_DATABASE_PATH || '/cube/data/security_analytics.duckdb',
  }),

  // CORS configuration for Superset integration
  http: {
    cors: {
      origin: ['http://localhost:8088', 'http://localhost:3000'],
      credentials: true,
    },
  },

  // API configuration
  apiSecret: process.env.CUBEJS_API_SECRET || 'your-cubejs-api-secret',
};
