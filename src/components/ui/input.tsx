import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      suppressHydrationWarning
      className={cn(
        "flex h-11 w-full border border-border bg-surface-2/80 px-3 font-display text-sm tracking-wide text-foreground placeholder:text-subtle outline-none transition-[border-color,box-shadow] duration-[var(--motion-quick)] focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";

export const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      "flex min-h-24 w-full border border-border bg-surface-2/80 px-3 py-2.5 font-display text-sm tracking-wide text-foreground placeholder:text-subtle outline-none transition-[border-color,box-shadow] duration-[var(--motion-quick)] focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40",
      className,
    )}
    {...props}
  />
));
Textarea.displayName = "Textarea";
