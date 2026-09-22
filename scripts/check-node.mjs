export function checkNode(version) {
  if (Number(version.split('.')[0]) !== 24) {
    throw new Error(
      `Node 24 is required; found ${version}. Run nvm install && nvm use in the repository.`,
    );
  }
}
checkNode(process.versions.node);
