import type { HTMLAttributes, ReactNode } from "react";

type CardProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
};

export default function Card({ children, className = "", ...rest }: CardProps) {
  return (
    <div
      className={`bg-card rounded-2xl p-6 shadow-sm border border-border ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}
