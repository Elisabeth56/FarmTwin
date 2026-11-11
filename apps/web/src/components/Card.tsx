import type { HTMLAttributes, ReactNode } from "react";

type CardProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
};

/** Surface panel on the ground colour. Separated by tone, not shadow. */
export default function Card({ children, className = "", ...rest }: CardProps) {
  return (
    <div className={`rounded-lg bg-surface p-6 ${className}`} {...rest}>
      {children}
    </div>
  );
}
