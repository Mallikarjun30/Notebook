import { Settings, Database, RefreshCw, AlertTriangle } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/PageHeader";
import { Card, CardHeader } from "@/components/shared/Card";
import { Button } from "@/components/ui/button";
import { toast } from "@/hooks/use-toast";
import { resetSystem } from "@/lib/api";

export default function SettingsPage() {
  const resetMutation = useMutation({
    mutationFn: resetSystem,
    onSuccess: () => {
      toast({
        title: "System reset",
        description: "All data has been cleared successfully.",
      });
    },
  });

  const handleReset = () => {
    resetMutation.mutate();
  };

  return (
    <div className="max-w-2xl mx-auto animate-fade-in">
      <PageHeader
        title="Settings"
        description="Manage your application preferences"
        icon={<Settings className="w-6 h-6" />}
      />

      <div className="grid gap-6">
        <Card>
          <CardHeader
            title="System Status"
            description="Current state of your knowledge base"
            icon={<Database className="w-5 h-5" />}
          />
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded-lg bg-muted/50">
              <p className="text-2xl font-semibold text-foreground">0</p>
              <p className="text-sm text-muted-foreground">Documents indexed</p>
            </div>
            <div className="p-4 rounded-lg bg-muted/50">
              <p className="text-2xl font-semibold text-foreground">0</p>
              <p className="text-sm text-muted-foreground">Vector embeddings</p>
            </div>
          </div>
        </Card>

        <Card variant="elevated">
          <CardHeader
            title="Danger Zone"
            description="Irreversible actions"
            icon={<AlertTriangle className="w-5 h-5 text-destructive" />}
          />
          <div className="p-4 rounded-lg border border-destructive/20 bg-destructive/5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h4 className="font-medium text-foreground">Reset System</h4>
                <p className="text-sm text-muted-foreground mt-1">
                  Clear all uploaded documents, vector embeddings, and cached data.
                  This action cannot be undone.
                </p>
              </div>
              <Button variant="destructive" onClick={handleReset} disabled={resetMutation.isPending}>
                <RefreshCw className="w-4 h-4 mr-2" />
                Reset All
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
