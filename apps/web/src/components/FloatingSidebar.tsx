import type { ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import Logo from "./Logo";

/** `also` lists other path prefixes that belong to the item, e.g. a farm's pages under Farms */
export type SidebarItem = { to: string; label: string; end?: boolean; also?: string[] };

type FloatingSidebarProps = {
  items: SidebarItem[];
  footer?: ReactNode;
};

/** The app's floating rail: logo, sections, and a footer slot (model status). Top bar on phones. */
export default function FloatingSidebar({ items, footer }: FloatingSidebarProps) {
  const { pathname } = useLocation();
  return (
    <nav
      aria-label="Main"
      className="sticky top-[var(--shell-top,1rem)] z-30 mx-4 flex items-center gap-2 rounded-pill bg-raised p-2 shadow-float md:fixed md:top-[var(--shell-top,1rem)] md:bottom-4 md:left-4 md:mx-0 md:w-56 md:flex-col md:items-stretch md:rounded-xl md:p-4"
    >
      <div className="px-2 md:mb-6">
        <Logo />
      </div>
      <ul className="flex flex-1 gap-1 overflow-x-auto md:flex-col">
        {items.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex min-h-11 items-center rounded-pill px-4 text-small whitespace-nowrap transition duration-150 ease-ui ${
                  isActive || item.also?.some((p) => pathname.startsWith(p)) ? "bg-brand-tint text-ink" : "text-ink-muted hover:bg-ink/5 hover:text-ink"
                }`
              }
            >
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
      {footer && <div className="hidden md:block">{footer}</div>}
    </nav>
  );
}
