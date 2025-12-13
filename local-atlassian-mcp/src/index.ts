#!/usr/bin/env node

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

const { ATLASSIAN_URL, ATLASSIAN_EMAIL, ATLASSIAN_TOKEN } = process.env;

function getAuthHeader(): string {
  if (!ATLASSIAN_EMAIL || !ATLASSIAN_TOKEN) {
    throw new Error('ATLASSIAN_EMAIL and ATLASSIAN_TOKEN must be set');
  }
  const credentials = Buffer.from(`${ATLASSIAN_EMAIL}:${ATLASSIAN_TOKEN}`).toString('base64');
  return `Basic ${credentials}`;
}

function getBaseUrl(): string {
  if (!ATLASSIAN_URL) {
    throw new Error('ATLASSIAN_URL must be set');
  }
  return ATLASSIAN_URL.replace(/\/$/, '');
}

async function fetchAtlassian(path: string): Promise<unknown> {
  const response = await fetch(`${getBaseUrl()}${path}`, {
    headers: {
      // biome-ignore lint/style/useNamingConvention: HTTP header names
      Authorization: getAuthHeader(),
      // biome-ignore lint/style/useNamingConvention: HTTP header names
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Atlassian API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

// Jira API helpers
function getJiraIssue(issueKey: string): Promise<unknown> {
  return fetchAtlassian(`/rest/api/3/issue/${issueKey}`);
}

function searchJira(jql: string, maxResults = 50): Promise<unknown> {
  const params = new URLSearchParams({
    jql,
    maxResults: String(maxResults),
  });
  return fetchAtlassian(`/rest/api/3/search/jql?${params}`);
}

function getMyJiraIssues(maxResults = 50): Promise<unknown> {
  return searchJira('assignee = currentUser() ORDER BY updated DESC', maxResults);
}

// Confluence API helpers
function getConfluencePage(pageId: string): Promise<unknown> {
  return fetchAtlassian(`/wiki/api/v2/pages/${pageId}?body-format=storage`);
}

function searchConfluence(query: string, limit = 25): Promise<unknown> {
  const params = new URLSearchParams({
    cql: `text ~ "${query}"`,
    limit: String(limit),
  });
  return fetchAtlassian(`/wiki/rest/api/content/search?${params}`);
}

// MCP Server setup
const server = new McpServer({ name: 'local-atlassian-mcp', version: '0.1.0' });

server.registerTool(
  'get_jira_issue',
  {
    description: 'Get a Jira issue by its key (e.g., PROJ-123)',
    inputSchema: z.object({
      issueKey: z.string().describe('The Jira issue key (e.g., PROJ-123)'),
    }),
  },
  async ({ issueKey }) => ({
    content: [{ type: 'text', text: JSON.stringify(await getJiraIssue(issueKey), null, 2) }],
  }),
);

server.registerTool(
  'search_jira',
  {
    description: 'Search Jira issues using JQL (Jira Query Language)',
    inputSchema: z.object({
      jql: z.string().describe('JQL query string'),
      maxResults: z.number().optional().describe('Maximum number of results (default: 50)'),
    }),
  },
  async ({ jql, maxResults }) => ({
    content: [{ type: 'text', text: JSON.stringify(await searchJira(jql, maxResults ?? 50), null, 2) }],
  }),
);

server.registerTool(
  'get_my_jira_issues',
  {
    description: 'Get Jira issues assigned to the current user',
    inputSchema: z.object({
      maxResults: z.number().optional().describe('Maximum number of results (default: 50)'),
    }),
  },
  async ({ maxResults }) => ({
    content: [{ type: 'text', text: JSON.stringify(await getMyJiraIssues(maxResults ?? 50), null, 2) }],
  }),
);

server.registerTool(
  'get_confluence_page',
  {
    description: 'Get a Confluence page by its ID',
    inputSchema: z.object({
      pageId: z.string().describe('The Confluence page ID'),
    }),
  },
  async ({ pageId }) => ({
    content: [{ type: 'text', text: JSON.stringify(await getConfluencePage(pageId), null, 2) }],
  }),
);

server.registerTool(
  'search_confluence',
  {
    description: 'Search Confluence pages by text content',
    inputSchema: z.object({
      query: z.string().describe('Search query text'),
      limit: z.number().optional().describe('Maximum number of results (default: 25)'),
    }),
  },
  async ({ query, limit }) => ({
    content: [{ type: 'text', text: JSON.stringify(await searchConfluence(query, limit ?? 25), null, 2) }],
  }),
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main();
