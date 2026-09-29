import { useState } from "react";
import { FileText, Plus, X, Wand2, Download, Loader2, ToggleLeft, ToggleRight } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/PageHeader";
import { Card, CardHeader } from "@/components/shared/Card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { toast } from "@/hooks/use-toast";
import { generateNotes } from "@/lib/api";

type TopicMode = "single" | "multiple";

export default function NotesPage() {
  const [basePrompt, setBasePrompt] = useState("");
  const [topicMode, setTopicMode] = useState<TopicMode>("single");
  const [singleTopics, setSingleTopics] = useState("");
  const [multipleTopics, setMultipleTopics] = useState<string[]>([""]);
  const [batchSize, setBatchSize] = useState("1");
  const [generatedNotes, setGeneratedNotes] = useState<string | null>(null);

  const generationMutation = useMutation({
    mutationFn: ({
      basePrompt,
      topics,
      batchSize,
    }: {
      basePrompt: string;
      topics: string[];
      batchSize: number;
    }) => generateNotes(basePrompt, topics, batchSize),
    onSuccess: (data) => {
      setGeneratedNotes(data);
      toast({
        title: "Notes generated successfully",
      });
    },
    onError: (error) => {
      toast({
        title: "Generation failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const addTopic = () => {
    setMultipleTopics([...multipleTopics, ""]);
  };

  const removeTopic = (index: number) => {
    if (multipleTopics.length > 1) {
      setMultipleTopics(multipleTopics.filter((_, i) => i !== index));
    }
  };

  const updateTopic = (index: number, value: string) => {
    const updated = [...multipleTopics];
    updated[index] = value;
    setMultipleTopics(updated);
  };

  const getTopics = (): string[] => {
    if (topicMode === "single") {
      return singleTopics
        .split("\n")
        .map((t) => t.trim())
        .filter((t) => t.length > 0);
    }
    return multipleTopics.filter((t) => t.trim().length > 0);
  };

  const handleGenerate = async () => {
    const topics = getTopics();

    if (topics.length === 0) {
      toast({
        title: "No topics provided",
        description: "Please add at least one topic to generate notes.",
        variant: "destructive",
      });
      return;
    }

    setGeneratedNotes(null);
    generationMutation.mutate({
      basePrompt: basePrompt || "Generate comprehensive notes about:",
      topics,
      batchSize: parseInt(batchSize) || 1,
    });
  };

  const handleDownload = () => {
    if (!generatedNotes) return;

    const blob = new Blob([generatedNotes], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "generated_notes.md";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };


  return (
    <div className="max-w-4xl mx-auto animate-fade-in">
      <PageHeader
        title="Generate Notes"
        description="Create structured notes from your uploaded documents"
        icon={<FileText className="w-6 h-6" />}
      />

      <div className="grid gap-6">
        {/* Base Prompt */}
        <Card>
          <CardHeader
            title="Base Prompt"
            description="Optional custom instructions for note generation"
          />
          <Textarea
            placeholder="Enter custom instructions (optional). Leave empty to use default prompt..."
            value={basePrompt}
            onChange={(e) => setBasePrompt(e.target.value)}
            className="min-h-[100px] resize-none"
          />
        </Card>

        {/* Topics Section */}
        <Card variant="elevated">
          <div className="flex items-start justify-between mb-4">
            <CardHeader
              title="Topics"
              description="Define topics to generate notes for"
              icon={<Wand2 className="w-5 h-5" />}
            />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setTopicMode(topicMode === "single" ? "multiple" : "single")}
              className="text-muted-foreground"
            >
              {topicMode === "single" ? (
                <>
                  <ToggleLeft className="w-4 h-4 mr-2" />
                  Bulk Mode
                </>
              ) : (
                <>
                  <ToggleRight className="w-4 h-4 mr-2" />
                  Individual Mode
                </>
              )}
            </Button>
          </div>

          {topicMode === "single" ? (
            <div className="space-y-2">
              <Label htmlFor="topics-textarea" className="text-sm text-muted-foreground">
                Enter one topic per line
              </Label>
              <Textarea
                id="topics-textarea"
                placeholder="Machine Learning Fundamentals&#10;Neural Network Architectures&#10;Gradient Descent Optimization"
                value={singleTopics}
                onChange={(e) => setSingleTopics(e.target.value)}
                className="min-h-[150px] font-mono text-sm"
              />
              <p className="text-xs text-muted-foreground">
                {getTopics().length} topic{getTopics().length !== 1 ? "s" : ""} detected
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {multipleTopics.map((topic, index) => (
                <div
                  key={index}
                  className="flex items-center gap-2 animate-slide-up"
                  style={{ animationDelay: `${index * 30}ms` }}
                >
                  <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary/10 text-primary text-sm font-medium">
                    {index + 1}
                  </div>
                  <Input
                    placeholder={`Topic ${index + 1}`}
                    value={topic}
                    onChange={(e) => updateTopic(index, e.target.value)}
                    className="flex-1"
                  />
                  {multipleTopics.length > 1 && (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => removeTopic(index)}
                      className="h-8 w-8 text-muted-foreground hover:text-destructive"
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              ))}
              <Button
                variant="outline"
                size="sm"
                onClick={addTopic}
                className="w-full mt-2"
              >
                <Plus className="w-4 h-4 mr-2" />
                Add Topic
              </Button>
            </div>
          )}
        </Card>

        {/* Options */}
        <Card>
          <CardHeader title="Options" />
          <div className="flex items-center gap-4">
            <div className="flex-1 max-w-[200px]">
              <Label htmlFor="batch-size" className="text-sm text-muted-foreground">
                Batch Size
              </Label>
              <Input
                id="batch-size"
                type="number"
                min="1"
                max="10"
                value={batchSize}
                onChange={(e) => setBatchSize(e.target.value)}
                className="mt-1"
              />
            </div>
            <p className="text-xs text-muted-foreground flex-1">
              Controls how many topics are processed simultaneously
            </p>
          </div>
        </Card>

        {/* Generate Button */}
        <Button
          variant="gradient"
          size="lg"
          onClick={handleGenerate}
          disabled={generationMutation.isPending || getTopics().length === 0}
          className="w-full"
        >
          {generationMutation.isPending ? (
            <>
              <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              Generating Notes...
            </>
          ) : (
            <>
              <Wand2 className="w-5 h-5 mr-2" />
              Generate Notes
            </>
          )}
        </Button>

        {/* Generated Output */}
        {generatedNotes && (
          <Card variant="elevated" className="animate-slide-up">
            <div className="flex items-center justify-between mb-4">
              <CardHeader
                title="Generated Notes"
                description="Preview your generated markdown notes"
              />
              <Button variant="outline" size="sm" onClick={handleDownload}>
                <Download className="w-4 h-4 mr-2" />
                Download .md
              </Button>
            </div>
            <div className="p-4 rounded-lg bg-muted/50 font-mono text-sm overflow-auto max-h-[400px]">
              <pre className="whitespace-pre-wrap text-foreground">{generatedNotes}</pre>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
