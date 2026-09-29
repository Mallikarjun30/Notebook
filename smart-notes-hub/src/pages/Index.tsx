import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

const Index = () => {
  const navigate = useNavigate();

  useEffect(() => {
    // Redirect to upload page as the default landing
    navigate("/upload", { replace: true });
  }, [navigate]);

  return null;
};

export default Index;
