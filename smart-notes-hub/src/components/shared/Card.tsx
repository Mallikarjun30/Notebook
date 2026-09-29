import { ReactNode, CSSProperties } from "react";
import { cn } from "@/lib/utils";

interface CardProps {
  children: ReactNode;
  className?: string;
  variant?: "default" | "elevated" | "glass";
  style?: CSSProperties;
}

export function Card({ children, className, variant = "default", style }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border p-6 transition-all duration-200",
        variant === "default" && "bg-card shadow-card",
        variant === "elevated" && "bg-card shadow-elevated hover:shadow-glow",
        variant === "glass" && "glass",
        className
      )}
      style={style}
    >
      {children}
    </div>
  );
}

interface CardHeaderProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
}

export function CardHeader({ title, description, icon, action }: CardHeaderProps) {
  return (
    <div className="flex items-start justify-between mb-4">
      <div className="flex items-center gap-3">
        {icon && (
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary/10 text-primary">
            {icon}
          </div>
        )}
        <div>
          <h3 className="font-semibold text-foreground">{title}</h3>
          {description && (
            <p className="text-sm text-muted-foreground">{description}</p>
          )}
        </div>
      </div>
      {action}
    </div>
  );
}
