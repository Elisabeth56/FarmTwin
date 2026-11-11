import { forwardRef, type SelectHTMLAttributes } from "react";

const Select = forwardRef<
  HTMLSelectElement,
  SelectHTMLAttributes<HTMLSelectElement>
>(function Select({ className = "", children, ...rest }, ref) {
  return (
    <select
      ref={ref}
      className={`w-full rounded-xl border border-border bg-white px-4 py-2.5 text-ink focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-colors ${className}`}
      {...rest}
    >
      {children}
    </select>
  );
});

export default Select;
