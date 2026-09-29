import { HelpCircle, Upload, FileText, MessageSquare, ExternalLink } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Card, CardHeader } from "@/components/shared/Card";

const features = [
  {
    icon: Upload,
    title: "Upload Documents",
    description: "Upload PDF files to build your knowledge base. Files are processed and indexed automatically for fast retrieval.",
    steps: [
      "Navigate to the Upload page",
      "Drag and drop PDFs or click to browse",
      "Wait for processing to complete",
      "Files are now searchable"
    ]
  },
  {
    icon: FileText,
    title: "Generate Notes",
    description: "Create structured notes from your documents by specifying topics. Choose between bulk mode or individual topic inputs.",
    steps: [
      "Go to the Notes page",
      "Optionally set a custom base prompt",
      "Enter your topics (one per line or individually)",
      "Click Generate to create notes",
      "Download the generated markdown file"
    ]
  },
  {
    icon: MessageSquare,
    title: "Chat with Documents",
    description: "Ask questions and get answers based on your uploaded documents. The AI searches your knowledge base for relevant information.",
    steps: [
      "Open the Chat page",
      "Type your question in the input field",
      "Press Enter or click Send",
      "Review the AI's response with citations"
    ]
  }
];

export default function HelpPage() {
  return (
    <div className="max-w-3xl mx-auto animate-fade-in">
      <PageHeader
        title="Help & Documentation"
        description="Learn how to use Smart Notes Studio"
        icon={<HelpCircle className="w-6 h-6" />}
      />

      <div className="grid gap-6">
        {features.map((feature, index) => {
          const Icon = feature.icon;
          return (
            <Card
              key={feature.title}
              variant="elevated"
              className="animate-slide-up"
              style={{ animationDelay: `${index * 100}ms` } as React.CSSProperties}
            >
              <CardHeader
                title={feature.title}
                description={feature.description}
                icon={<Icon className="w-5 h-5" />}
              />
              <div className="mt-4">
                <h4 className="text-sm font-medium text-foreground mb-2">How to use:</h4>
                <ol className="space-y-2">
                  {feature.steps.map((step, stepIndex) => (
                    <li
                      key={stepIndex}
                      className="flex items-start gap-3 text-sm text-muted-foreground"
                    >
                      <span className="flex items-center justify-center w-5 h-5 rounded-full bg-primary/10 text-primary text-xs font-medium flex-shrink-0 mt-0.5">
                        {stepIndex + 1}
                      </span>
                      {step}
                    </li>
                  ))}
                </ol>
              </div>
            </Card>
          );
        })}

        <Card>
          <CardHeader title="Need More Help?" />
          <div className="flex items-center gap-4">
            <a
              href="#"
              className="flex items-center gap-2 text-sm text-primary hover:underline"
            >
              <ExternalLink className="w-4 h-4" />
              View API Documentation
            </a>
            <span className="text-muted-foreground">•</span>
            <a
              href="#"
              className="flex items-center gap-2 text-sm text-primary hover:underline"
            >
              <ExternalLink className="w-4 h-4" />
              Report an Issue
            </a>
          </div>
        </Card>
      </div>
    </div>
  );
}
