import pandas as pd
from flow import create_data_profiling_flow

def main():
    """Main function for data profiling"""
    
    # Load the test dataset
    print("Loading patient data...")
    df = pd.read_csv("test/patients.csv")
    print(f"Loaded {len(df)} rows and {len(df.columns)} columns")
    
    # Initialize shared store with the data profiling structure
    shared = {
        "dataframe": df,
        "sample_data": "",
        "profile_results": {
            "duplicates": {},
            "table_summary": "",
            "column_descriptions": {},
            "data_types": {},
            "missing_values": {},
            "uniqueness": {},
            "unusual_values": {}
        },
        "final_report": ""
    }
    
    # Create and run the data profiling flow
    print("\nStarting data profiling analysis...")
    profiling_flow = create_data_profiling_flow()
    profiling_flow.run(shared)
    
    # Save the report first (avoid console encoding issues)
    with open("data_profiling_report.md", "w", encoding="utf-8") as f:
        f.write(shared["final_report"])
    print("\nReport saved to: data_profiling_report.md")
    print(f"Report contains {len(shared['final_report'])} characters")
    
    # Show basic stats instead of full report
    print("\n" + "="*50 + " SUMMARY " + "="*50)
    dup = shared["profile_results"]["duplicates"]
    print(f"✓ Analyzed {dup['total_rows']} rows, {len(shared['dataframe'].columns)} columns")
    print(f"✓ Found {dup['count']} duplicate rows ({dup['percentage']:.1f}%)")
    print(f"✓ Analysis complete - check data_profiling_report.md for full details")
    print("="*108)

if __name__ == "__main__":
    main()
