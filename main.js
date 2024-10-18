const core = require("@actions/core");
const github = require("@actions/github");

try {
  const hubRepo = core.getInput("hub-repo");
  const payload = github.context.payload;
  core.info(JSON.stringify(payload, null, 2));
  core.summary.addDetails("Payload", JSON.stringify(payload, null, 2));
} catch (error) {
  core.setFailed(error.message);
}
