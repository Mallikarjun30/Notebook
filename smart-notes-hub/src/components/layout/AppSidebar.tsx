import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import { 
  Upload, 
  FileText, 
  MessageSquare, 
  ChevronLeft, 
  ChevronRight,
  Sparkles,
  Settings,
  HelpCircle
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const navItems = [
  { path: "/upload", label: "Upload", icon: Upload, description: "Manage PDFs" },
  { path: "/notes", label: "Generate Notes", icon: FileText, description: "Create notes" },
  { path: "/chat", label: "Chat", icon: MessageSquare, description: "Ask questions" },
];

const bottomItems = [
  { path: "/settings", label: "Settings", icon: Settings },
  { path: "/help", label: "Help", icon: HelpCircle },
];

export function AppSidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();

  return (
    <aside
      className={cn(
        "flex flex-col h-screen bg-sidebar border-r border-sidebar-border transition-all duration-300 ease-in-out",
        collapsed ? "w-16" : "w-64"
      )}
    >
      {/* Logo */}
      <div className={cn(
        "flex items-center h-16 px-4 border-b border-sidebar-border",
        collapsed ? "justify-center" : "gap-3"
      )}>
        <div className="flex items-center justify-center w-8 h-8 rounded-lg gradient-primary shadow-glow">
          <Sparkles className="w-4 h-4 text-primary-foreground" />
        </div>
        {!collapsed && (
          <div className="animate-fade-in">
            <h1 className="text-sm font-semibold text-sidebar-foreground">Smart Notes</h1>
            <p className="text-xs text-muted-foreground">Studio</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          const Icon = item.icon;

          const linkContent = (
            <NavLink
              to={item.path}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group",
                isActive
                  ? "bg-sidebar-accent text-sidebar-primary"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
              )}
            >
              <Icon className={cn(
                "w-5 h-5 transition-transform duration-200",
                isActive && "text-sidebar-primary",
                "group-hover:scale-110"
              )} />
              {!collapsed && (
                <div className="animate-slide-in-left">
                  <span className="font-medium text-sm">{item.label}</span>
                  <p className="text-xs text-muted-foreground">{item.description}</p>
                </div>
              )}
              {isActive && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-sidebar-primary animate-pulse-subtle" />
              )}
            </NavLink>
          );

          if (collapsed) {
            return (
              <Tooltip key={item.path} delayDuration={0}>
                <TooltipTrigger asChild>
                  {linkContent}
                </TooltipTrigger>
                <TooltipContent side="right" className="flex flex-col">
                  <span className="font-medium">{item.label}</span>
                  <span className="text-xs text-muted-foreground">{item.description}</span>
                </TooltipContent>
              </Tooltip>
            );
          }

          return <div key={item.path}>{linkContent}</div>;
        })}
      </nav>

      {/* Bottom Section */}
      <div className="p-3 border-t border-sidebar-border space-y-1">
        {bottomItems.map((item) => {
          const Icon = item.icon;
          const content = (
            <NavLink
              to={item.path}
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-sidebar-foreground/60 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground transition-all duration-200"
            >
              <Icon className="w-4 h-4" />
              {!collapsed && <span className="text-sm">{item.label}</span>}
            </NavLink>
          );

          if (collapsed) {
            return (
              <Tooltip key={item.path} delayDuration={0}>
                <TooltipTrigger asChild>{content}</TooltipTrigger>
                <TooltipContent side="right">{item.label}</TooltipContent>
              </Tooltip>
            );
          }

          return <div key={item.path}>{content}</div>;
        })}

        {/* Collapse Toggle */}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setCollapsed(!collapsed)}
          className={cn(
            "w-full justify-center text-sidebar-foreground/60 hover:text-sidebar-foreground hover:bg-sidebar-accent/50",
            !collapsed && "justify-start px-3"
          )}
        >
          {collapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <>
              <ChevronLeft className="w-4 h-4" />
              <span className="text-sm">Collapse</span>
            </>
          )}
        </Button>
      </div>
    </aside>
  );
}
