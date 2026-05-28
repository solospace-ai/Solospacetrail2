"""
DAG Planner - Creates and manages agent execution graphs with topological sorting
"""
import networkx as nx
from typing import List, Dict, Any, Set, Tuple
from app.models import AgentCreate, AgentResponse


class DAGPlanner:
    """Plans and manages directed acyclic graphs for agent execution."""
    
    def __init__(self):
        self.graph = nx.DiGraph()
    
    def build_graph(self, agents: List[AgentCreate]) -> nx.DiGraph:
        """
        Build a directed graph from agent definitions.
        
        Args:
            agents: List of agent definitions with dependencies
            
        Returns:
            NetworkX DiGraph representing agent dependencies
        """
        self.graph = nx.DiGraph()
        
        # Add nodes
        for agent in agents:
            self.graph.add_node(
                agent.name,
                data=agent
            )
        
        # Add edges based on dependencies
        for agent in agents:
            for dep in agent.dependencies:
                # Edge goes from dependency to dependent
                if dep in [a.name for a in agents]:
                    self.graph.add_edge(dep, agent.name)
        
        return self.graph
    
    def validate_dag(self) -> Tuple[bool, str]:
        """
        Validate that the graph is a valid DAG (no cycles).
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not self.graph.nodes():
                return True, ""
            
            # Check for cycles
            cycles = list(nx.simple_cycles(self.graph))
            if cycles:
                cycle_str = " -> ".join(cycles[0])
                return False, f"Circular dependency detected: {cycle_str}"
            
            return True, ""
        except Exception as e:
            return False, str(e)
    
    def compute_execution_levels(self) -> Dict[str, int]:
        """
        Compute execution levels for parallel execution.
        Agents at the same level can run in parallel.
        
        Returns:
            Dict mapping agent names to execution levels
        """
        if not self.graph.nodes():
            return {}
        
        # Use longest path to determine levels
        levels = {}
        
        # Topological sort
        topo_order = list(nx.topological_sort(self.graph))
        
        for node in topo_order:
            predecessors = list(self.graph.predecessors(node))
            if not predecessors:
                levels[node] = 0
            else:
                levels[node] = max(levels[p] for p in predecessors) + 1
        
        return levels
    
    def get_parallel_groups(self) -> List[List[str]]:
        """
        Get groups of agents that can execute in parallel.
        
        Returns:
            List of lists, where each inner list contains agent names at the same level
        """
        levels = self.compute_execution_levels()
        
        # Group by level
        level_groups: Dict[int, List[str]] = {}
        for agent_name, level in levels.items():
            if level not in level_groups:
                level_groups[level] = []
            level_groups[level].append(agent_name)
        
        # Sort by level and return
        return [level_groups[level] for level in sorted(level_groups.keys())]
    
    def get_topological_order(self) -> List[str]:
        """
        Get agents in topological order (dependencies first).
        
        Returns:
            List of agent names in execution order
        """
        return list(nx.topological_sort(self.graph))
    
    def get_dependencies(self, agent_name: str) -> List[str]:
        """Get direct dependencies of an agent."""
        return list(self.graph.predecessors(agent_name))
    
    def get_dependents(self, agent_name: str) -> List[str]:
        """Get agents that depend on this agent."""
        return list(self.graph.successors(agent_name))
    
    def add_agent(self, agent: AgentCreate) -> bool:
        """Add an agent to the graph."""
        self.graph.add_node(agent.name, data=agent)
        
        # Add edges for dependencies
        for dep in agent.dependencies:
            if dep in self.graph.nodes():
                self.graph.add_edge(dep, agent.name)
        
        return True
    
    def remove_agent(self, agent_name: str) -> bool:
        """Remove an agent from the graph."""
        if agent_name in self.graph.nodes():
            self.graph.remove_node(agent_name)
            return True
        return False
    
    def add_dependency(self, from_agent: str, to_agent: str) -> bool:
        """Add a dependency edge between agents."""
        if from_agent in self.graph.nodes() and to_agent in self.graph.nodes():
            self.graph.add_edge(from_agent, to_agent)
            return True
        return False
    
    def remove_dependency(self, from_agent: str, to_agent: str) -> bool:
        """Remove a dependency edge between agents."""
        if self.graph.has_edge(from_agent, to_agent):
            self.graph.remove_edge(from_agent, to_agent)
            return True
        return False
    
    def get_graph_info(self) -> Dict[str, Any]:
        """Get information about the graph."""
        return {
            "node_count": self.graph.number_of_nodes(),
            "edge_count": self.graph.number_of_edges(),
            "is_dag": nx.is_directed_acyclic_graph(self.graph),
            "parallel_groups": len(self.get_parallel_groups()),
            "topological_order": self.get_topological_order()
        }


def plan_agent_execution(agents: List[AgentCreate]) -> Dict[str, Any]:
    """
    Plan agent execution from a list of agent definitions.
    
    Args:
        agents: List of agent definitions
        
    Returns:
        Execution plan with levels, order, and validation
    """
    planner = DAGPlanner()
    planner.build_graph(agents)
    
    is_valid, error = planner.validate_dag()
    
    if not is_valid:
        return {
            "valid": False,
            "error": error,
            "plan": None
        }
    
    levels = planner.compute_execution_levels()
    parallel_groups = planner.get_parallel_groups()
    topo_order = planner.get_topological_order()
    
    return {
        "valid": True,
        "error": None,
        "plan": {
            "levels": levels,
            "parallel_groups": parallel_groups,
            "execution_order": topo_order,
            "graph_info": planner.get_graph_info()
        }
    }
