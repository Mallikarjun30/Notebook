import { useState, useCallback } from "react";
import { Upload, FileText, X, CheckCircle2, AlertCircle, RotateCcw } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/PageHeader";
import { Card, CardHeader } from "@/components/shared/Card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { toast } from "@/hooks/use-toast";
import { uploadFiles, resetSystem } from "@/lib/api";

interface UploadedFile {
  id: string;
  name: string;
  size: number;
  status: "uploading" | "success" | "error";
  progress: number;
  file: File;
}

export default function UploadPage() {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  const uploadMutation = useMutation({
    mutationFn: (files: File[]) => uploadFiles(files),
    onSuccess: (data, variables) => {
      setFiles((prev) =>
        prev.map((f) =>
          variables.some((v) => v.name === f.name)
            ? { ...f, status: "success", progress: 100 }
            : f
        )
      );
      toast({
        title: "Upload complete",
        description: `${data.files.length} new file(s) processed and indexed.`,
      });
    },
    onError: (error, variables) => {
      setFiles((prev) =>
        prev.map((f) =>
          variables.some((v) => v.name === f.name)
            ? { ...f, status: "error", progress: 0 }
            : f
        )
      );
      toast({
        title: "Upload failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const resetMutation = useMutation({
    mutationFn: resetSystem,
    onSuccess: () => {
      setFiles([]);
      toast({
        title: "System reset",
        description: "All files and indexes have been cleared.",
      });
    },
  });

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFiles = Array.from(e.dataTransfer.files).filter(
      (file) => file.type === "application/pdf"
    );

    if (droppedFiles.length === 0) {
      toast({
        title: "Invalid file type",
        description: "Please upload PDF files only.",
        variant: "destructive",
      });
      return;
    }

    addFiles(droppedFiles);
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      addFiles(selectedFiles);
    }
  };

  const addFiles = (newFiles: File[]) => {
    const filesToUpload = newFiles.filter(
      (file) => !files.some((f) => f.name === file.name && f.status !== "error")
    );

    const uploadedFiles: UploadedFile[] = filesToUpload.map((file) => ({
      id: Math.random().toString(36).substr(2, 9),
      name: file.name,
      size: file.size,
      status: "uploading" as const,
      progress: 0,
      file: file,
    }));

    setFiles((prev) => [...prev, ...uploadedFiles]);
    uploadMutation.mutate(filesToUpload);
  };

  const removeFile = (fileId: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== fileId));
  };

  const handleReset = () => {
    resetMutation.mutate();
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };


  return (
    <div className="max-w-4xl mx-auto animate-fade-in">
      <PageHeader
        title="Upload Documents"
        description="Upload PDF files to build your knowledge base"
        icon={<Upload className="w-6 h-6" />}
        actions={
          files.length > 0 && (
            <Button variant="outline" onClick={handleReset}>
              <RotateCcw className="w-4 h-4 mr-2" />
              Reset All
            </Button>
          )
        }
      />

      {/* Drop Zone */}
      <Card className="mb-6">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={cn(
            "relative flex flex-col items-center justify-center p-12 border-2 border-dashed rounded-xl transition-all duration-200 cursor-pointer group",
            isDragging
              ? "border-primary bg-primary/5 scale-[1.01]"
              : "border-border hover:border-primary/50 hover:bg-muted/50"
          )}
        >
          <input
            type="file"
            accept=".pdf"
            multiple
            onChange={handleFileInput}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          />
          
          <div className={cn(
            "flex items-center justify-center w-16 h-16 rounded-2xl mb-4 transition-all duration-200",
            isDragging ? "bg-primary/20 scale-110" : "bg-muted group-hover:bg-primary/10"
          )}>
            <Upload className={cn(
              "w-8 h-8 transition-colors duration-200",
              isDragging ? "text-primary" : "text-muted-foreground group-hover:text-primary"
            )} />
          </div>
          
          <h3 className="text-lg font-medium text-foreground mb-1">
            {isDragging ? "Drop your files here" : "Drop PDF files here"}
          </h3>
          <p className="text-sm text-muted-foreground mb-4">
            or click to browse from your computer
          </p>
          <p className="text-xs text-muted-foreground">
            Supports: PDF files up to 50MB
          </p>
        </div>
      </Card>

      {/* File List */}
      {files.length > 0 && (
        <Card variant="elevated">
          <CardHeader
            title="Uploaded Files"
            description={`${files.length} file${files.length > 1 ? "s" : ""} in queue`}
            icon={<FileText className="w-5 h-5" />}
          />

          <div className="space-y-3">
            {files.map((file, index) => (
              <div
                key={file.id}
                className="flex items-center gap-4 p-4 rounded-lg bg-muted/50 animate-slide-up"
                style={{ animationDelay: `${index * 50}ms` }}
              >
                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary/10">
                  <FileText className="w-5 h-5 text-primary" />
                </div>

                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm text-foreground truncate">
                    {file.name}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {formatFileSize(file.size)}
                  </p>
                  
                  {file.status === "uploading" && (
                    <div className="mt-2 h-1.5 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full gradient-primary transition-all duration-300 ease-out rounded-full"
                        style={{ width: `${file.progress}%` }}
                      />
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  {file.status === "uploading" && (
                    <span className="text-xs text-muted-foreground">
                      {Math.round(file.progress)}%
                    </span>
                  )}
                  {file.status === "success" && (
                    <CheckCircle2 className="w-5 h-5 text-green-500" />
                  )}
                  {file.status === "error" && (
                    <AlertCircle className="w-5 h-5 text-destructive" />
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-destructive"
                    onClick={() => removeFile(file.id)}
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Empty State */}
      {files.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <FileText className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-sm">No files uploaded yet</p>
          <p className="text-xs mt-1">Upload PDFs to start building your knowledge base</p>
        </div>
      )}
    </div>
  );
}
