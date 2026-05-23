/** Active state for main sidebar / mobile nav links. */
export function isNavActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  if (href === "/contracts") {
    return pathname === "/contracts" || pathname.startsWith("/contracts/");
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}
