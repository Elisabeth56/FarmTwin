import type { LabelHTMLAttributes, ReactNode } from "react";

type Props = LabelHTMLAttributes<HTMLLabelElement> & {
  required?: boolean;
  children: ReactNode;
};

export default function FieldLabel({
  required,
  className = "",
  children,
  ...rest
}: Props) {
  return (
    <label
      className={`block text-sm font-medium text-ink-muted mb-1.5 ${className}`}
      {...rest}
    >
      {children}
      {required && <span className="text-risk-high ml-0.5">*</span>}
    </label>
  );
}
