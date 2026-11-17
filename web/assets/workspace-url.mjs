export const workspaceUrl = (path, profile, extra={}) => {
  const query = new URLSearchParams(extra);
  if(profile)query.set('profile',profile);
  return path + (query.size?'?'+query:'');
};
