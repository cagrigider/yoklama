import { test as base, expect } from "@playwright/test";
import { resetSharedDb } from "./api";

export const test = base.extend<{ cleanDb: void }>({
  cleanDb: [
    async ({}, use) => {
      resetSharedDb();
      await use();
    },
    { auto: true },
  ],
});

export { expect };
