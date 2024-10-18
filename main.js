const core = require("@actions/core");
const github = require("@actions/github");
const fs = require("fs");

try {
  const hubRepo = core.getInput("hub-repo");
  const payload = github.context.payload;
  core.info(JSON.stringify(payload, null, 2));
  core.info("Hub Repo: " + hubRepo);

  core.info("Files: " + fs.readdirSync("./").join("\n"));

} catch (error) {
  core.setFailed(error.message);
}
