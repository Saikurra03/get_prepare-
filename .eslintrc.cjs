module.exports = {
  env: {
    browser: true,
    es2021: true,
  },
  extends: ['eslint:recommended'],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
  },
  rules: {
    'no-console': 'off',
    'no-unused-vars': ['warn', { varsIgnorePattern: '^__', argsIgnorePattern: '^__' }],
    eqeqeq: 'error',
    curly: 'error',
    'no-implicit-coercion': 'warn',
  },
};