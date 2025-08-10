from pocketflow import Flow
from nodes import (
    DuplicateDetectionNode, 
    TableSummaryNode, 
    ColumnDescriptionNode,
    DataTypeAnalysisNode, 
    MissingValuesAnalysisNode, 
    UniquenessAnalysisNode,
    UnusualValuesDetectionNode, 
    GenerateReportNode
)

def create_data_profiling_flow():
    """Create and return a data profiling flow."""
    
    # Create all nodes
    duplicate_node = DuplicateDetectionNode()
    summary_node = TableSummaryNode()
    column_desc_node = ColumnDescriptionNode()
    data_type_node = DataTypeAnalysisNode()
    missing_values_node = MissingValuesAnalysisNode()
    uniqueness_node = UniquenessAnalysisNode()
    unusual_values_node = UnusualValuesDetectionNode()
    report_node = GenerateReportNode()
    
    # Connect nodes in sequence (following the workflow design)
    duplicate_node >> summary_node >> column_desc_node >> data_type_node >> missing_values_node >> uniqueness_node >> unusual_values_node >> report_node
    
    # Create flow starting with duplicate detection
    return Flow(start=duplicate_node)