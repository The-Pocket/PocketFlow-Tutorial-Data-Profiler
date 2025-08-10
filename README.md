# PocketFlow Data Profiling Tool

An intelligent data profiling tool powered by LLMs that provides deep, contextual analysis of your datasets beyond traditional statistical metrics.

## 🎯 What This Tool Does

This tool performs comprehensive data profiling through a 7-step workflow:

1. **Duplicate Detection** - Identifies and analyzes duplicate rows with recommendations
2. **Table Summary** - Generates high-level description of what your data represents
3. **Column Descriptions** - Analyzes each column with meaningful descriptions and naming suggestions
4. **Data Type Analysis** - Recommends optimal data types for each column
5. **Missing Values Analysis** - Categorizes missing values as meaningful vs problematic
6. **Uniqueness Analysis** - Identifies potential unique identifier columns
7. **Unusual Values Detection** - Detects outliers, anomalies, and data quality issues

## 🚀 How to Run

### Prerequisites

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set up your LLM:**

The tool uses OpenAI by default. Set your API key:
```bash
export OPENAI_API_KEY="your-key-here"
```

To use your own LLM or different providers, check out the [PocketFlow LLM documentation](https://the-pocket.github.io/PocketFlow/utility_function/llm.html) and modify `utils/call_llm.py` accordingly.

**Test your LLM setup:**
```bash
python utils/call_llm.py
```

### Running the Tool

```bash
python main.py
```

By default, it analyzes the sample patient dataset in `test/patients.csv`. To analyze your own data, modify `main.py`:

```python
# Replace this line:
df = pd.read_csv("test/patients.csv")

# With your data:
df = pd.read_csv("path/to/your/data.csv")
```

### Output

The tool generates:
- **Console summary** with key statistics
- **Markdown report** saved as `data_profiling_report.md` with comprehensive analysis

## 📊 Example Results

From the sample patient dataset (60 rows, 27 columns):

- ✅ Detected invalid SSN formats (test data with "999" prefix)
- ✅ Identified name contamination (numeric suffixes in names)
- ✅ Found meaningful missing patterns (83% missing death dates = living patients)
- ✅ Recommended data type conversions (dates to datetime64, categories for demographics)
- ✅ Identified unique identifiers (UUID primary key, SSN)

## 🏗️ Architecture

Built with [PocketFlow](https://github.com/The-Pocket/PocketFlow) - a minimalist LLM framework:

- **Workflow pattern** for sequential processing pipeline
- **BatchNode** for efficient parallel column analysis
- **YAML-based** structured outputs with validation
- **Intelligent LLM analysis** for contextual understanding

## 📁 Project Structure

```
├── main.py                 # Entry point
├── flow.py                 # Flow orchestrator
├── nodes.py                # All profiling nodes
├── utils/
│   └── call_llm.py        # LLM utility (customize for your provider)
├── test/
│   └── patients.csv       # Sample dataset
└── docs/
    └── design.md          # Design documentation
```

## 🔧 Customization

### Using Different LLM Providers

Edit `utils/call_llm.py` to use your preferred LLM:
- Claude (Anthropic)
- Google Gemini
- Azure OpenAI
- Local models (Ollama)

See the [PocketFlow LLM guide](https://the-pocket.github.io/PocketFlow/utility_function/llm.html) for examples.

### Analyzing Different Data Types

The tool works with any pandas DataFrame. You can:
- Load from CSV, Excel, JSON, Parquet
- Connect to databases
- Use API data

Just ensure your data is loaded as a pandas DataFrame before running the flow.

## 🎓 Tutorial

This project demonstrates **Agentic Coding** with [PocketFlow](https://github.com/The-Pocket/PocketFlow). Want to learn more?

- Check out the [Agentic Coding Guidance](https://the-pocket.github.io/PocketFlow/guide.html)
- Watch the [YouTube Tutorial](https://www.youtube.com/@ZacharyLLM?sub_confirmation=1)

## 📝 License

This project is a tutorial example for PocketFlow.
