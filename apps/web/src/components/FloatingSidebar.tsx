import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import Logo from "./Logo";

export type SidebarItem = { to: string; label: string; end?: boolean };

type FloatingSidebarProps = {
  items: SidebarItem[];
  footer?: ReactNode;
};

/** The app's floating rail: logo, sections, and a footer slot (model status). Top bar on phones. */
export default function FloatingSidebar({ items, footer }: FloatingSidebarProps) {
  return (
    <nav
      aria-label="Main"
      className="sticky top-4 z-30 mx-4 flex items-center gap-2 rounded-pill bg-raised p-2 shadow-float md:fixed md:top-4 md:bottom-4 md:left-4 md:mx-0 md:w-56 md:flex-col md:items-stretch md:rounded-xl md:p-4"
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
                  isActive ? "bg-brand-tint text-ink" : "text-ink-muted hover:bg-ink/5 hover:text-ink"
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
