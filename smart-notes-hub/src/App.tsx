import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import Index from "./pages/Index";
import UploadPage from "./pages/UploadPage";
import NotesPage from "./pages/NotesPage";
import ChatPage from "./pages/ChatPage";
import SettingsPage from "./pages/SettingsPage";
import HelpPage from "./pages/HelpPage";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <Toaster />
    <Sonner />
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Index />} />
        <Route
          path="/upload"
          element={
            <AppLayout>
              <UploadPage />
            </AppLayout>
          }
        />
        <Route
          path="/notes"
          element={
            <AppLayout>
              <NotesPage />
            </AppLayout>
          }
        />
        <Route
          path="/chat"
          element={
            <AppLayout>
              <ChatPage />
            </AppLayout>
          }
        />
        <Route
          path="/settings"
          element={
            <AppLayout>
              <SettingsPage />
            </AppLayout>
          }
        />
        <Route
          path="/help"
          element={
            <AppLayout>
              <HelpPage />
            </AppLayout>
          }
        />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  </QueryClientProvider>
);

export default App;
