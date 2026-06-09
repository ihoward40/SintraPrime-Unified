module.exports = {
  testEnvironment: "node",
  passWithNoTests: true,

  testPathIgnorePatterns: [
    "/node_modules/",
    "/apps/",
    "/mobile/",
    "/web/",
    "/.venv/",
  ],

  modulePathIgnorePatterns: [
    "<rootDir>/apps/",
    "<rootDir>/mobile/",
    "<rootDir>/web/",
    "<rootDir>/.venv/",
  ],
};
