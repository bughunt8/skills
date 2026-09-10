#!/usr/bin/env node
import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";

const targets = {
  staging: "https://mediumvioletred-coyote-692292.hostingersite.com/",
  production: "https://skills.ronald.ng/"
};

export function checkTarget(environment, value) {
  assert(Object.hasOwn(targets, environment), "unknown deployment environment");
  // Normalize only the optional final slash. No credentials, alternate host,
  // path, query string or fragment can turn verification into a different check.
  assert(value && value.trim() === value, "a nonempty verification URL is required");
  // Never interpolate the rejected value into the message. assert.equal builds a
  // diagnostic containing the actual value, which would print any credentials
  // embedded in a mistyped URL into a public log.
  assert(
    value.replace(/\/$/, "") === targets[environment].replace(/\/$/, ""),
    "verification URL does not match the deployment environment"
  );
  return targets[environment];
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    console.log(`Verified deployment target: ${checkTarget(...process.argv.slice(2))}`);
  } catch (error) {
    console.error(`Invalid deployment target: ${error.message}`);
    process.exitCode = 1;
  }
}
