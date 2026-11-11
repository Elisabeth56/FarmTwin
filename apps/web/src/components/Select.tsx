import { forwardRef, type SelectHTMLAttributes } from "react";

const Select = forwardRef<
  HTMLSelectElement,
  SelectHTMLAttributes<HTMLSelectElement>
>(function Select({ className = "", children, ...rest }, ref) {
  return (
    <select
      ref={ref}
      className={`w-full rounded-md border border-hairline bg-raised px-4 py-2.5 text-ink focus:border-brand focus:ring-1 focus:ring-brand outline-none transition-colors ${className}`}
      {...rest}
    >
      {children}
    </select>
  );
});

export default Select;
