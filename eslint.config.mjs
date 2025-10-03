import globals from "globals";
import path from "node:path";
import { fileURLToPath } from "node:url";
import js from "@eslint/js";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const compat = new FlatCompat({
    baseDirectory: __dirname,
    recommendedConfig: js.configs.recommended,
    allConfig: js.configs.all,
});

export default [{
    ignores: [
    "**/node_modules/",
    "**/.venv/",
    "**/dist/",
    "**/build/",
    "**/*.min.js",
    "**/.eslintcache",
    "**/.mypy_cache/",
    "**/.pytest_cache/",
    "**/__pycache__/",
    "**/htmlcov/",
    "**/.coverage",
    "**/.nyc_output",
    "**/.env",
    "**/.env.local",
    "**/.env.development.local",
    "**/.env.test.local",
    "**/.env.production.local",
    "**/*.log",
    "**/npm-debug.log*",
    "**/yarn-debug.log*",
    "**/yarn-error.log*",
    "**/*.pyc",
    "**/*.pyo",
    "**/*.pyd",
    "**/backend/",
    "**/tests/",
    "**/.git/",
    "**/*.tmp",
    "**/*.temp",
    "**/.vscode/",
    "**/.idea/",
    "**/*.swp",
    "**/*.swo",
    "**/.DS_Store",
    "**/.DS_Store?",
    "**/._*",
    "**/.Spotlight-V100",
    "**/.Trashes",
    "**/ehthumbs.db",
    "**/Thumbs.db",
    ],
}, {
    ...js.configs.recommended,

    languageOptions: {
        globals: {
            ...globals.browser,
            ...globals.webextensions,
            chrome: "readonly",
        },

        ecmaVersion: "latest",
        sourceType: "module",
    },

    rules: {
        indent: ["error", 2],
        "linebreak-style": ["error", "unix"],
        quotes: ["error", "double"],
        semi: ["error", "always"],
        "no-unused-vars": "off",
        "no-console": "off",
        "no-debugger": "error",
        "no-undef": "warn",
        eqeqeq: "error",
        "no-trailing-spaces": "error",
        "comma-dangle": ["error", "always-multiline"],
        "object-curly-spacing": ["error", "always"],
        "array-bracket-spacing": ["error", "never"],

        "space-before-function-paren": ["error", {
            anonymous: "always",
            named: "never",
            asyncArrow: "always",
        }],

        "keyword-spacing": "error",
        "space-infix-ops": "error",

        "brace-style": ["error", "1tbs", {
            allowSingleLine: true,
        }],

        camelcase: ["error", {
            properties: "never",
        }],

        "max-len": ["error", {
            code: 120,
            ignoreUrls: true,
            ignoreStrings: true,
        }],
    },
}];
