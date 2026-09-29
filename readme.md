# Notes Generator Web App

An AI-powered document processing system that revolutionizes study habits by converting PDF materials into intelligent, structured notes. This full-stack solution combines cutting-edge NLP through Google's Gemini API with robust PDF engineering to create comprehensive study guides, research summaries, and technical documentation.

**Key Innovation**: Automates the knowledge extraction process through:
- Context-aware document analysis
- Semantic relationship mapping
- Adaptive content prioritization
- Multi-document synthesis

Ideal for:
- 🎓 Students processing academic papers
- 👩🏫 Educators creating course materials
- 📚 Researchers synthesizing literature reviews
- 💼 Professionals generating technical reports

**Technical Edge**:
- Hybrid vector-based caching system (MD5 + semantic hashing)
- Batch processing pipeline with error recovery
- Asynchronous I/O operations for large document handling
- CSS3-powered PDF templating engine

## Features ✨

- **PDF Document Processing**: Upload multiple PDF files for analysis
- **AI-Powered Note Generation**: Utilizes Gemini API for intelligent note creation
- **Batch Processing**: Handle multiple topics simultaneously
- **Document Caching**: MD5-based caching to avoid reprocessing
- **Styled PDF Output**: Professional formatting with code highlighting
- **RESTful API**: Built with Flask and CORS support

## Installation 🚀

### Prerequisites
- Python 3.9+
- Docker, Docker compose
- Google Gemini API key

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/notes-generator.git
   cd notes-generator
   ```

2. Create `.env` file:
   ```env
   GEMINI_API_KEY_QUERY=
   GEMINI_API_KEY_GENERATE=
   ```

3. Install dependencies (Not needed if using docker):
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application 🖥️

### Docker (Recommended)
```bash
docker compose up
```

### Local Development
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Open `index.html` in your browser to access the frontend.

## Usage 📚

1. **Upload PDFs** through the web interface
2.  **Enter a base prompt** : This prompt is common throuughout all the topics
3. **Enter topics** you want covered (seperator is '\n'):
   ```plaintext
   Machine Learning, Artificial Intelligence, Neural Networks
   ```
4. **Set the counter** : This is the number of topics that is sent to the gemini API in each itreration
5. **Generate Notes** with optional custom base prompt:
   ```plaintext
   Create detailed study notes explaining the fundamentals of:
   ```
6. **Download** formatted PDF report

## API Documentation 🔧

### Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/upload` | POST | Upload PDF documents (max 16MB) |
| `/generate` | POST | Generate notes PDF |
| `/reset` | POST | Clear all processed documents |

## Project Structure 🗂️

```
├── app.py                 # Main application entry point
├── processing.py          # PDF processing and AI integration
├── document_cache.py      # Document caching implementation
├── uploads/               # Temporary PDF storage
├── templates/             # Frontend components
├── requirements.txt       # Python dependencies
└── .env                   # Environment configuration
```

## Configuration ⚙️

Create a `.env` file with these required settings:

```env
GEMINI_API_KEY_QUERY=
GEMINI_API_KEY_GENERATE=
```


**Note:** Obtain your Gemini API key from [Google AI Studio](https://aistudio.google.com/).

## Contributing 🤝

Contributions welcome! Please follow these steps:
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License 📄

Distributed under the MIT License. See `LICENSE` for more information.

## Acknowledgements 🙏

- Google Gemini API
- Flask & WeasyPrint communities
- PDF processing contributors
