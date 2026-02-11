import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { type LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value?: string | number;
  children?: React.ReactNode;
  subtitle?: string;
  icon?: LucideIcon;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  className?: string;
}

export function StatCard({
  title,
  value,
  children,
  subtitle,
  icon: Icon,
  trend,
  className,
}: StatCardProps) {
  return (
    <Card className={cn("bg-card", className)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        {Icon && <Icon className="h-4 w-4 text-muted-foreground" />}
      </CardHeader>
      <CardContent>
        {children ?? <div className="text-3xl font-bold text-primary">{value}</div>}
        {subtitle && <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>}
        {trend && (
          <p className={cn("mt-1 text-xs", trend.isPositive ? "text-success" : "text-destructive")}>
            {trend.isPositive ? "+" : ""}
            {trend.value}% from last week
          </p>
        )}
      </CardContent>
    </Card>
  );
}
