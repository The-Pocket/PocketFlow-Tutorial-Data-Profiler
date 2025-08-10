import pandas as pd
import yaml
from pocketflow import Node, BatchNode
from utils.call_llm import call_llm

def truncate_cell(value, max_length=50):
    """Truncate cell values for display purposes"""
    if pd.isna(value):
        return value
    str_value = str(value)
    if len(str_value) > max_length:
        return str_value[:max_length] + "..."
    return str_value


class DuplicateDetectionNode(Node):
    def prep(self, shared):
        df = shared["dataframe"]
        
        # Find duplicate rows
        duplicate_rows = df[df.duplicated(keep=False)]
        duplicate_count = len(duplicate_rows) - len(duplicate_rows.drop_duplicates())
        duplicate_percentage = (duplicate_count / len(df)) * 100 if len(df) > 0 else 0
        
        # Get sample of duplicate rows for LLM analysis
        sample_duplicates = ""
        if duplicate_count > 0:
            sample_df = duplicate_rows.head(10).applymap(truncate_cell)
            sample_duplicates = sample_df.to_csv(index=False, quoting=1)
        
        # Get basic table info for context
        table_sample = df.head(5).applymap(truncate_cell).to_csv(index=False, quoting=1)
        
        return {
            "duplicate_count": duplicate_count,
            "duplicate_percentage": duplicate_percentage,
            "total_rows": len(df),
            "sample_duplicates": sample_duplicates,
            "table_sample": table_sample
        }

    def exec(self, prep_res):
        if prep_res["duplicate_count"] == 0:
            return {
                "should_remove": False,
                "analysis": "No duplicate rows found in the dataset."
            }
        
        prompt = f"""
You have a table with {prep_res["total_rows"]} total rows and {prep_res["duplicate_count"]} duplicate rows ({prep_res["duplicate_percentage"]:.2f}%).

Sample of the table:
{prep_res["table_sample"]}

Sample duplicate rows:
{prep_res["sample_duplicates"]}

Analyze these duplicates and decide whether they should be removed.

Return in YAML format:
```yaml
should_remove: true/false
analysis: "Brief analysis explaining why duplicates should/shouldn't be removed"
```
"""
        
        response = call_llm(prompt)
        yaml_str = response.split("```yaml")[1].split("```")[0].strip()
        result = yaml.safe_load(yaml_str)
        
        assert "should_remove" in result
        assert "analysis" in result
        assert isinstance(result["should_remove"], bool)
        assert isinstance(result["analysis"], str)
        
        return result

    def post(self, shared, prep_res, exec_res):
        shared["profile_results"]["duplicates"] = {
            "count": prep_res["duplicate_count"],
            "percentage": prep_res["duplicate_percentage"],
            "total_rows": prep_res["total_rows"],
            "should_remove": exec_res["should_remove"],
            "analysis": exec_res["analysis"],
            "sample_rows": prep_res["sample_duplicates"]
        }

class TableSummaryNode(Node):
    def prep(self, shared):
        df = shared["dataframe"]
        
        # Create a sample for LLM analysis
        sample_df = df.head(50).applymap(truncate_cell)
        sample_data = sample_df.to_csv(index=False, quoting=1)
        
        # Basic info
        column_names = list(df.columns)
        row_count = len(df)
        
        return {
            "sample_data": sample_data,
            "column_names": column_names,
            "row_count": row_count
        }

    def exec(self, prep_res):
        columns_str = ", ".join(prep_res["column_names"])
        
        prompt = f"""
You have a table with {prep_res["row_count"]} rows and the following columns: {columns_str}

Sample data:
{prep_res["sample_data"]}

Task: Summarize what this table represents.
- Highlight: Include and highlight ALL column names as **Column_Name**
- Structure: Start with the big picture, then explain how columns are related
- Requirement: ALL column names must be mentioned and **highlighted**. Use exact column names (case sensitive)
- Style: Use a few short sentences with simple words

Example: "The table contains information about ... with **Customer_ID**, **Order_Date**, and **Amount**..."

Your summary:
"""
        
        return call_llm(prompt)

    def post(self, shared, prep_res, exec_res):
        shared["profile_results"]["table_summary"] = exec_res
        return "default"

class ColumnDescriptionNode(BatchNode):
    def prep(self, shared):
        df = shared["dataframe"]
        columns = list(df.columns)
        
        # Process columns in chunks of 10
        chunks = []
        for i in range(0, len(columns), 10):
            chunk_columns = columns[i:i + 10]
            chunk_df = df[chunk_columns].head(5).applymap(truncate_cell)
            chunk_sample = chunk_df.to_csv(index=False, quoting=1)
            chunks.append((chunk_columns, chunk_sample))
        
        return chunks

    def exec(self, chunk_data):
        chunk_columns, chunk_sample = chunk_data
        
        prompt = f"""
You have the following table columns and sample data:
{chunk_sample}

For each column, provide a short description and suggest a better name if needed.

Return in YAML format:
```yaml
{chunk_columns[0]}:
  description: "Short description"
  suggested_name: "new_column_name"
...
```
"""
        
        response = call_llm(prompt)
        yaml_str = response.split("```yaml")[1].split("```")[0].strip()
        result = yaml.safe_load(yaml_str)
        
        # Validate all columns are present with required fields
        for col in chunk_columns:
            assert col in result, f"Column {col} missing from result"
            assert "description" in result[col], f"Description missing for {col}"
            assert "suggested_name" in result[col], f"Suggested name missing for {col}"
            assert isinstance(result[col]["description"], str)
            assert isinstance(result[col]["suggested_name"], str)
        
        return result

    def post(self, shared, prep_res, exec_res_list):
        # Combine results from all chunks
        all_descriptions = {}
        for chunk_result in exec_res_list:
            all_descriptions.update(chunk_result)
        
        # Convert to the expected format (now already in the right structure from YAML)
        shared["profile_results"]["column_descriptions"] = all_descriptions
        return "default"

class DataTypeAnalysisNode(Node):
    def prep(self, shared):
        df = shared["dataframe"]
        
        # Get current data types
        current_types = {col: str(df[col].dtype) for col in df.columns}
        
        # Get sample data
        sample_df = df.head(10).applymap(truncate_cell)
        sample_data = sample_df.to_csv(index=False, quoting=1)
        
        return {
            "sample_data": sample_data,
            "current_types": current_types,
            "columns": list(df.columns)
        }

    def exec(self, prep_res):
        types_info = "\n".join([f"{col}: currently {dtype}" for col, dtype in prep_res["current_types"].items()])
        valid_types = ["int64", "float64", "object", "datetime64", "bool", "category"]
        
        prompt = f"""
You have the following table with current data types:
{types_info}

Sample data:
{prep_res["sample_data"]}

For each column, suggest the most appropriate data type from: {valid_types}

Return in YAML format:
```yaml
column1:
  suggested_type: "int64"
  reason: "Contains only integer values"
...
```
"""
        
        response = call_llm(prompt)
        yaml_str = response.split("```yaml")[1].split("```")[0].strip()
        result = yaml.safe_load(yaml_str)
        
        # Validate all columns are present with required fields
        for col in prep_res["columns"]:
            assert col in result, f"Column {col} missing from result"
            assert "suggested_type" in result[col], f"Suggested type missing for {col}"
            assert "reason" in result[col], f"Reason missing for {col}"
            assert result[col]["suggested_type"] in valid_types, f"Invalid type for {col}: {result[col]['suggested_type']}"
            assert isinstance(result[col]["reason"], str)
        
        return result

    def post(self, shared, prep_res, exec_res):
        # Combine current and suggested types
        data_types = {}
        for col in prep_res["columns"]:
            data_types[col] = {
                "current_type": prep_res["current_types"][col],
                "suggested_type": exec_res[col]["suggested_type"],
                "reason": exec_res[col]["reason"]
            }
        
        shared["profile_results"]["data_types"] = data_types
        return "default"

class MissingValuesAnalysisNode(Node):
    def prep(self, shared):
        df = shared["dataframe"]
        
        # Calculate missing values
        missing_info = {}
        for col in df.columns:
            missing_count = df[col].isna().sum()
            if missing_count > 0:
                missing_percentage = (missing_count / len(df)) * 100
                missing_info[col] = {
                    "count": missing_count,
                    "percentage": missing_percentage
                }
        
        # Get sample data
        sample_df = df.head(10).applymap(truncate_cell)
        sample_data = sample_df.to_csv(index=False, quoting=1)
        
        return {
            "missing_info": missing_info,
            "sample_data": sample_data,
            "total_rows": len(df)
        }

    def exec(self, prep_res):
        if not prep_res["missing_info"]:
            return {
                "reasoning": "No missing values found in any columns.",
                "columns_analysis": {}
            }
        
        missing_desc = "\n".join([
            f"{col}: {info['count']} missing ({info['percentage']:.1f}%)" 
            for col, info in prep_res["missing_info"].items()
        ])
        
        prompt = f"""
You have a table with the following missing values:
{missing_desc}

Sample data for context:
{prep_res["sample_data"]}

For each column with missing values, determine if missing values are meaningful or problematic.

Return in YAML format:
```yaml
overall_analysis: "Brief overall analysis"
columns:
  column_name:
    is_meaningful: true/false
    reason: "Brief explanation"
  ...
```
"""
        
        response = call_llm(prompt)
        yaml_str = response.split("```yaml")[1].split("```")[0].strip()
        result = yaml.safe_load(yaml_str)
        
        # Validate structure
        assert "overall_analysis" in result
        assert "columns" in result
        assert isinstance(result["overall_analysis"], str)
        assert isinstance(result["columns"], dict)
        
        # Validate each column analysis
        for col in prep_res["missing_info"].keys():
            assert col in result["columns"], f"Missing analysis for column {col}"
            assert "is_meaningful" in result["columns"][col]
            assert "reason" in result["columns"][col]
            assert isinstance(result["columns"][col]["is_meaningful"], bool)
            assert isinstance(result["columns"][col]["reason"], str)
        
        return result

    def post(self, shared, prep_res, exec_res):
        missing_values = {}
        
        # Process columns with missing values
        for col, info in prep_res["missing_info"].items():
            analysis = exec_res["columns"][col]
            missing_values[col] = {
                "count": info["count"],
                "percentage": info["percentage"],
                "is_meaningful": analysis["is_meaningful"],
                "reason": analysis["reason"]
            }
        
        # Add columns with no missing values
        df = shared["dataframe"]
        for col in df.columns:
            if col not in missing_values:
                missing_values[col] = {
                    "count": 0,
                    "percentage": 0.0,
                    "is_meaningful": True,
                    "reason": "No missing values"
                }
        
        shared["profile_results"]["missing_values"] = missing_values
        shared["profile_results"]["missing_analysis"] = exec_res["overall_analysis"]
        return "default"

class UniquenessAnalysisNode(Node):
    def prep(self, shared):
        df = shared["dataframe"]
        
        # Calculate uniqueness for each column
        uniqueness_info = {}
        for col in df.columns:
            unique_count = df[col].nunique()
            total_count = len(df)
            unique_percentage = (unique_count / total_count) * 100 if total_count > 0 else 0
            
            uniqueness_info[col] = {
                "unique_count": unique_count,
                "total_count": total_count,
                "unique_percentage": unique_percentage
            }
        
        # Get sample data and table summary for context
        sample_df = df.head(10).applymap(truncate_cell)
        sample_data = sample_df.to_csv(index=False, quoting=1)
        table_summary = shared["profile_results"].get("table_summary", "")
        
        # Get highly unique columns (>90% unique)
        highly_unique = {col: info for col, info in uniqueness_info.items() 
                        if info["unique_percentage"] > 90}
        
        return {
            "uniqueness_info": uniqueness_info,
            "highly_unique": highly_unique,
            "sample_data": sample_data,
            "table_summary": table_summary
        }

    def exec(self, prep_res):
        if not prep_res["highly_unique"]:
            return {
                "reasoning": "No columns found that could serve as candidate keys.",
                "candidate_keys": {}
            }
        
        highly_unique_desc = "\n".join([
            f"{col}: {info['unique_count']}/{info['total_count']} unique ({info['unique_percentage']:.1f}%)"
            for col, info in prep_res["highly_unique"].items()
        ])
        
        prompt = f"""
Table context: {prep_res["table_summary"]}

Sample data:
{prep_res["sample_data"]}

The following columns have high uniqueness:
{highly_unique_desc}

Analyze which columns could serve as candidate keys (unique identifiers) for this table.
Consider:
- What each row represents in this table
- Whether the column values should be unique across all rows
- Avoid continuous numerical values (like temperatures, prices) that happen to be unique in the sample

Return in YAML format:
```yaml
reasoning: "Analysis of which columns can serve as identifiers..."
candidate_keys:
  column_name:
    is_candidate_key: true/false
    explanation: "Why this column is/isn't a good candidate key"
  ...
```
"""
        
        response = call_llm(prompt)
        yaml_str = response.split("```yaml")[1].split("```")[0].strip()
        return yaml.safe_load(yaml_str)

    def post(self, shared, prep_res, exec_res):
        uniqueness = {}
        
        for col, info in prep_res["uniqueness_info"].items():
            candidate_analysis = exec_res.get("candidate_keys", {}).get(col, {})
            uniqueness[col] = {
                "unique_count": info["unique_count"],
                "unique_percentage": info["unique_percentage"],
                "is_candidate_key": candidate_analysis.get("is_candidate_key", False),
                "explanation": candidate_analysis.get("explanation", "")
            }
        
        shared["profile_results"]["uniqueness"] = uniqueness
        shared["profile_results"]["uniqueness_reasoning"] = exec_res.get("reasoning", "")
        return "default"

class UnusualValuesDetectionNode(BatchNode):
    def prep(self, shared):
        df = shared["dataframe"]
        columns = list(df.columns)
        
        # Create analysis tasks for each column
        column_tasks = []
        for col in columns:
            # Get sample of distinct values (up to 1000 for inspection)
            sample_values = df[col].dropna().drop_duplicates().head(1000)
            sample_list = [truncate_cell(val, 100) for val in sample_values]
            
            column_tasks.append({
                "column_name": col,
                "sample_values": sample_list,
                "data_type": str(df[col].dtype)
            })
        
        return column_tasks

    def exec(self, column_task):
        col_name = column_task["column_name"]
        sample_values = column_task["sample_values"]
        data_type = column_task["data_type"]
        
        if not sample_values:
            return {
                "column_name": col_name,
                "has_unusual": False,
                "explanation": "No values to analyze (all missing)"
            }
        
        values_str = ", ".join([f"'{val}'" for val in sample_values[:15]])
        
        prompt = f"""
Column "{col_name}" (type: {data_type}) has the following sample values:
{values_str}

Check if there are any unusual values that seem wrong or inconsistent.

Return in YAML format:
```yaml
has_unusual: true/false
explanation: "Brief explanation of findings"
```
"""
        
        response = call_llm(prompt)
        yaml_str = response.split("```yaml")[1].split("```")[0].strip()
        result = yaml.safe_load(yaml_str)
        
        # Validate structure
        assert "has_unusual" in result
        assert "explanation" in result
        assert isinstance(result["has_unusual"], bool)
        assert isinstance(result["explanation"], str)
        
        result["column_name"] = col_name
        return result

    def post(self, shared, prep_res, exec_res_list):
        unusual_values = {}
        
        for result in exec_res_list:
            col_name = result["column_name"]
            unusual_values[col_name] = {
                "has_unusual": result["has_unusual"],
                "explanation": result["explanation"]
            }
        
        shared["profile_results"]["unusual_values"] = unusual_values
        return "default"

class GenerateReportNode(Node):
    def prep(self, shared):
        return shared["profile_results"]

    def exec(self, profile_results):
        # Generate a comprehensive report
        report_sections = []
        
        # Title
        report_sections.append("# Data Profiling Report\n")
        
        # Table Summary
        if "table_summary" in profile_results:
            report_sections.append("## Table Summary")
            report_sections.append(profile_results["table_summary"])
            report_sections.append("")
        
        # Duplicates
        if "duplicates" in profile_results:
            dup = profile_results["duplicates"]
            report_sections.append("## Duplicate Analysis")
            report_sections.append(f"- **Total rows**: {dup['total_rows']}")
            report_sections.append(f"- **Duplicate rows**: {dup['count']} ({dup['percentage']:.2f}%)")
            report_sections.append(f"- **Should remove**: {dup['should_remove']}")
            report_sections.append(f"- **Analysis**: {dup['analysis']}")
            report_sections.append("")
        
        # Column Descriptions
        if "column_descriptions" in profile_results:
            report_sections.append("## Column Descriptions")
            for col, info in profile_results["column_descriptions"].items():
                suggested = f" → *{info['suggested_name']}*" if info['suggested_name'] != col else ""
                report_sections.append(f"- **{col}**{suggested}: {info['description']}")
            report_sections.append("")
        
        # Data Types
        if "data_types" in profile_results:
            report_sections.append("## Data Type Analysis")
            changes_found = False
            for col, info in profile_results["data_types"].items():
                if info['suggested_type'] != info['current_type']:
                    report_sections.append(f"- **{col}**: {info['current_type']} → *{info['suggested_type']}* ({info['reason']})")
                    changes_found = True
            if not changes_found:
                report_sections.append("- All data types are appropriate")
            report_sections.append("")
        
        # Missing Values
        if "missing_values" in profile_results:
            report_sections.append("## Missing Values Analysis")
            if "missing_analysis" in profile_results:
                report_sections.append(f"**Overview**: {profile_results['missing_analysis']}")
                report_sections.append("")
            
            problematic_missing = []
            meaningful_missing = []
            
            for col, info in profile_results["missing_values"].items():
                if info['count'] > 0:
                    entry = f"**{col}**: {info['count']} missing ({info['percentage']:.1f}%) - {info['reason']}"
                    if info['is_meaningful']:
                        meaningful_missing.append(entry)
                    else:
                        problematic_missing.append(entry)
            
            if problematic_missing:
                report_sections.append("### Problematic Missing Values")
                for entry in problematic_missing:
                    report_sections.append(f"- {entry}")
                report_sections.append("")
            
            if meaningful_missing:
                report_sections.append("### Likely Meaningful Missing Values") 
                for entry in meaningful_missing:
                    report_sections.append(f"- {entry}")
                report_sections.append("")
        
        # Uniqueness
        if "uniqueness" in profile_results:
            report_sections.append("## Uniqueness Analysis")
            candidate_keys = []
            highly_unique = []
            
            for col, info in profile_results["uniqueness"].items():
                if info['is_candidate_key']:
                    candidate_keys.append(f"**{col}**: {info['explanation']}")
                elif info['unique_percentage'] > 50:
                    highly_unique.append(f"**{col}**: {info['unique_percentage']:.1f}% unique")
            
            if candidate_keys:
                report_sections.append("### Candidate Key Columns")
                for key in candidate_keys:
                    report_sections.append(f"- {key}")
                report_sections.append("")
                
            if highly_unique:
                report_sections.append("### Highly Unique Columns")
                for col in highly_unique:
                    report_sections.append(f"- {col}")
                report_sections.append("")
        
        # Unusual Values
        if "unusual_values" in profile_results:
            report_sections.append("## Unusual Values Detection")
            unusual_found = []
            
            for col, info in profile_results["unusual_values"].items():
                if info['has_unusual']:
                    unusual_found.append(f"**{col}**: {info['explanation']}")
            
            if unusual_found:
                for finding in unusual_found:
                    report_sections.append(f"- {finding}")
            else:
                report_sections.append("- No unusual values detected")
            report_sections.append("")
        
        return "\n".join(report_sections)

    def post(self, shared, prep_res, exec_res):
        shared["final_report"] = exec_res
        print("Data profiling complete! Report generated.")
        return "default"