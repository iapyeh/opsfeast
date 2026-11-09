// Fixed, decorative SVGs. Labels are provided by each native link or control.
const paths={
  home:'M3 10 12 3l9 7v10H3Z M9 20v-7h6v7',
  hosts:'M4 4h16v6H4Z M4 14h16v6H4Z M7 7h.01 M7 17h.01',
  recipes:'M5 3h14v18H5Z M8 7h8 M8 11h8 M8 15h5',
  work:'M8 5H4v16h16V5h-4 M8 3h8v4H8Z M8 12l2 2 5-5',
  logs:'M4 5h16 M4 12h16 M4 19h16 M8 3v4 M16 10v4 M11 17v4',
  apps:'M3 3h7v7H3Z M14 3h7v7h-7Z M3 14h7v7H3Z M14 14h7v7h-7Z',
  settings:'M9 3h6l1 4 4 1v8l-4 1-1 4H9l-1-4-4-1V8l4-1Z M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0',
  learn:'M3 4h7l2 2 2-2h7v15h-7l-2 2-2-2H3Z M12 6v15',
  docs:'M6 3h9l4 4v14H6Z M14 3v5h5 M9 12h7 M9 16h5',
  skills:'m12 3 9 9-9 9-9-9Z M8 12h8 M12 8v8'
};
export function uiIcon(name){
  if(!Object.hasOwn(paths,name))throw new Error('unknown_ui_icon');
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="${paths[name]}"/></svg>`;
}
