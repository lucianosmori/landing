import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const workLog = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/work-log" }),
  schema: z.object({
    month: z.string(),                   // e.g. "2026-03"
    monthStart: z.coerce.date(),         // e.g. 2026-03-01
    title: z.string(),
    summary: z.string().optional(),
    tags: z.array(z.string()).default([]),
    draft: z.boolean().default(false),
  }),
});

const writing = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/writing" }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    pubDate: z.coerce.date(),
    updatedDate: z.coerce.date().optional(),
    tags: z.array(z.string()).default([]),
    draft: z.boolean().default(false),
  }),
});

export const collections = {
  "work-log": workLog,
  writing,
};
