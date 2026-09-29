import { useState, useRef, useEffect } from "react";
import { MessageSquare, Send, Bot, User, Loader2, Trash2 } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/PageHeader";
import { Card } from "@/components/shared/Card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { chat } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const chatMutation = useMutation({
    mutationFn: (prompt: string) => chat(prompt),
    onSuccess: (data) => {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    },
    onError: (error) => {
      toast({
        title: "Chat failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();

    const trimmedInput = input.trim();
    if (!trimmedInput || chatMutation.isPending) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: trimmedInput,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");

    chatMutation.mutate(trimmedInput);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const clearChat = () => {
    setMessages([]);
  };


  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col max-w-4xl mx-auto animate-fade-in">
      <PageHeader
        title="Chat with Documents"
        description="Ask questions about your uploaded PDFs"
        icon={<MessageSquare className="w-6 h-6" />}
        actions={
          messages.length > 0 && (
            <Button variant="outline" size="sm" onClick={clearChat}>
              <Trash2 className="w-4 h-4 mr-2" />
              Clear Chat
            </Button>
          )
        }
      />

      {/* Messages Container */}
      <Card className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center py-12">
              <div className="w-16 h-16 rounded-2xl gradient-primary flex items-center justify-center mb-4 shadow-glow">
                <Bot className="w-8 h-8 text-primary-foreground" />
              </div>
              <h3 className="text-lg font-medium text-foreground mb-2">
                Start a conversation
              </h3>
              <p className="text-sm text-muted-foreground max-w-md">
                Ask questions about your uploaded documents. I'll search through
                your knowledge base and provide relevant answers.
              </p>
              <div className="mt-6 flex flex-wrap gap-2 justify-center">
                {[
                  "What are the main topics covered?",
                  "Summarize the key findings",
                  "Explain the methodology",
                ].map((suggestion) => (
                  <Button
                    key={suggestion}
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      setInput(suggestion);
                      textareaRef.current?.focus();
                    }}
                    className="text-xs"
                  >
                    {suggestion}
                  </Button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={message.id}
                className={cn(
                  "flex gap-3 animate-slide-up",
                  message.role === "user" ? "justify-end" : "justify-start"
                )}
                style={{ animationDelay: `${index * 50}ms` }}
              >
                {message.role === "assistant" && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-lg gradient-primary flex items-center justify-center">
                    <Bot className="w-4 h-4 text-primary-foreground" />
                  </div>
                )}
                <div
                  className={cn(
                    "max-w-[80%] rounded-2xl px-4 py-3",
                    message.role === "user"
                      ? "bg-primary text-primary-foreground rounded-br-md"
                      : "bg-muted text-foreground rounded-bl-md"
                  )}
                >
                  <div className="text-sm whitespace-pre-wrap">
                    {message.content}
                  </div>
                  <div
                    className={cn(
                      "text-xs mt-1 opacity-60",
                      message.role === "user"
                        ? "text-primary-foreground"
                        : "text-muted-foreground"
                    )}
                  >
                    {message.timestamp.toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </div>
                </div>
                {message.role === "user" && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-secondary flex items-center justify-center">
                    <User className="w-4 h-4 text-secondary-foreground" />
                  </div>
                )}
              </div>
            ))
          )}

          {chatMutation.isPending && (
            <div className="flex gap-3 animate-slide-up">
              <div className="flex-shrink-0 w-8 h-8 rounded-lg gradient-primary flex items-center justify-center">
                <Bot className="w-4 h-4 text-primary-foreground" />
              </div>
              <div className="bg-muted rounded-2xl rounded-bl-md px-4 py-3">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Searching documents...
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t border-border p-4">
          <form onSubmit={handleSubmit} className="flex gap-3">
            <div className="flex-1 relative">
              <Textarea
                ref={textareaRef}
                placeholder="Ask a question about your documents..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                className="min-h-[52px] max-h-[200px] resize-none pr-12"
                rows={1}
              />
              <Button
                type="submit"
                size="icon"
                disabled={!input.trim() || chatMutation.isPending}
                className="absolute right-2 bottom-2 h-8 w-8"
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </form>
          <p className="text-xs text-muted-foreground mt-2 text-center">
            Press Enter to send, Shift+Enter for new line
          </p>
        </div>
      </Card>
    </div>
  );
}
