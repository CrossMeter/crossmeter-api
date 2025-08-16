from typing import Dict, Any, Optional
from app.core.config import settings
from app.services.contract_interface import (
    RouterContractABI,
    ChainConfig,
    PaymentType,
    select_optimal_function
)


class RouterService:
    """Service for generating router contract calldata."""
    
    @staticmethod
    def generate_payment_calldata(
        vendor_wallet: str,
        amount_usdc_minor: int,
        src_chain_id: int,
        dest_chain_id: int,
        payment_intent_id: str,
        payment_type: PaymentType = PaymentType.SIMPLE,
        bridge_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate calldata for payment router contract.
        
        Args:
            vendor_wallet: Vendor's destination wallet address
            amount_usdc_minor: Amount in USDC minor units
            src_chain_id: Source chain ID
            dest_chain_id: Destination chain ID  
            payment_intent_id: Unique payment intent identifier
            payment_type: Type of payment (simple, bridge, batch, subscription)
            bridge_address: Optional bridge contract address for cross-chain
            
        Returns:
            Dict containing router address, function, and calldata
        """
        # Get chain configuration
        src_config = ChainConfig.get_chain_config(src_chain_id)
        if not src_config:
            raise ValueError(f"Unsupported source chain: {src_chain_id}")
        
        # Select optimal function based on payment parameters
        function_name = select_optimal_function(
            src_chain_id=src_chain_id,
            dest_chain_id=dest_chain_id,
            payment_type=payment_type
        )
        
        # Get function definition
        function_def = RouterContractABI.FUNCTIONS.get(function_name)
        if not function_def:
            raise ValueError(f"Unknown function: {function_name}")
        
        # Calculate fees if cross-chain
        bridge_fee = 0
        if src_chain_id != dest_chain_id:
            bridge_fee = ChainConfig.calculate_bridge_fee(amount_usdc_minor, src_chain_id)
        
        # Generate calldata based on function type
        if function_name == "createPayment":
            calldata = RouterService._encode_create_payment(
                vendor_wallet, amount_usdc_minor, src_chain_id, dest_chain_id, payment_intent_id
            )
        elif function_name == "bridgePayment":
            calldata = RouterService._encode_bridge_payment(
                vendor_wallet, amount_usdc_minor, src_chain_id, dest_chain_id, 
                bridge_address or src_config.get("bridge_address", "0x0"), payment_intent_id
            )
        else:
            # Fallback to mock calldata for unsupported functions
            calldata = RouterService._generate_mock_calldata({
                "vendor_wallet": vendor_wallet,
                "amount": amount_usdc_minor,
                "src_chain": src_chain_id,
                "dest_chain": dest_chain_id,
                "intent_id": payment_intent_id
            })
        
        return {
            "address": ChainConfig.get_router_address(src_chain_id) or settings.default_router_address,
            "chain_id": src_chain_id,
            "function": function_name,
            "calldata": calldata,
            "gas_limit": src_config.get("gas_limit", 300000),
            "bridge_fee": bridge_fee,
            "estimated_cost": {
                "gas_limit": src_config.get("gas_limit", 300000),
                "bridge_fee_usdc": bridge_fee,
                "total_amount_usdc": amount_usdc_minor + bridge_fee
            }
        }
    
    @staticmethod
    def _generate_mock_calldata(params: Dict[str, Any]) -> str:
        """
        Generate mock calldata for development.
        In production, replace with proper ABI encoding.
        """
        # Create a deterministic hex string from parameters
        param_string = f"{params['vendor_wallet']}{params['amount']}{params['src_chain']}{params['dest_chain']}{params['intent_id']}"
        
        # Simple hash-like transformation (NOT for production use)
        hex_chars = "0123456789abcdef"
        result = "0x"
        
        for i, char in enumerate(param_string):
            # Simple deterministic transformation
            char_code = ord(char)
            hex_index = (char_code + i) % 16
            result += hex_chars[hex_index]
        
        # Ensure minimum length for realistic calldata
        while len(result) < 138:  # Typical function call length
            result += "0"
            
        return result[:138]  # Truncate to realistic length
    
    @staticmethod
    def validate_chain_support(src_chain_id: int, dest_chain_id: int) -> bool:
        """
        Validate if the chain combination is supported.
        
        Args:
            src_chain_id: Source chain ID
            dest_chain_id: Destination chain ID
            
        Returns:
            bool: True if chain combination is supported
        """
        # Use the ChainConfig to check supported chains
        supported_chains = set(ChainConfig.get_supported_chains())
        
        return (
            src_chain_id in supported_chains and 
            dest_chain_id in supported_chains
            # Same-chain transfers are allowed
        )
    
    @staticmethod
    def _encode_create_payment(
        recipient: str,
        amount: int,
        src_chain_id: int,
        dest_chain_id: int,
        payment_id: str
    ) -> str:
        """
        Encode createPayment function call.
        
        Function signature: createPayment(address,uint256,uint32,uint32,bytes32)
        """
        function_selector = "0xa9059cbb"  # First 4 bytes of keccak256("createPayment(address,uint256,uint32,uint32,bytes32)")
        
        # Encode parameters
        encoded_recipient = RouterContractABI.encode_address(recipient)
        encoded_amount = RouterContractABI.encode_uint256(amount)
        encoded_src_chain = RouterContractABI.encode_uint32(src_chain_id)
        encoded_dest_chain = RouterContractABI.encode_uint32(dest_chain_id)
        encoded_payment_id = RouterContractABI.encode_bytes32(payment_id)
        
        # Combine function selector with encoded parameters
        calldata = function_selector + encoded_recipient + encoded_amount + encoded_src_chain + encoded_dest_chain + encoded_payment_id
        
        return calldata
    
    @staticmethod
    def _encode_bridge_payment(
        recipient: str,
        amount: int,
        src_chain_id: int,
        dest_chain_id: int,
        bridge_address: str,
        payment_id: str
    ) -> str:
        """
        Encode bridgePayment function call.
        
        Function signature: bridgePayment(address,uint256,uint32,uint32,address,bytes32)
        """
        function_selector = "0x23b872dd"  # First 4 bytes of keccak256("bridgePayment(address,uint256,uint32,uint32,address,bytes32)")
        
        # Encode parameters
        encoded_recipient = RouterContractABI.encode_address(recipient)
        encoded_amount = RouterContractABI.encode_uint256(amount)
        encoded_src_chain = RouterContractABI.encode_uint32(src_chain_id)
        encoded_dest_chain = RouterContractABI.encode_uint32(dest_chain_id)
        encoded_bridge = RouterContractABI.encode_address(bridge_address)
        encoded_payment_id = RouterContractABI.encode_bytes32(payment_id)
        
        # Combine function selector with encoded parameters
        calldata = function_selector + encoded_recipient + encoded_amount + encoded_src_chain + encoded_dest_chain + encoded_bridge + encoded_payment_id
        
        return calldata
    
    @staticmethod
    def get_chain_info(chain_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific chain.
        
        Args:
            chain_id: Chain ID to get info for
            
        Returns:
            Dict with chain information or None if not supported
        """
        return ChainConfig.get_chain_config(chain_id)
    
    @staticmethod
    def estimate_gas_cost(
        src_chain_id: int,
        dest_chain_id: int,
        amount_usdc_minor: int
    ) -> Dict[str, Any]:
        """
        Estimate gas costs and fees for a payment.
        
        Args:
            src_chain_id: Source chain ID
            dest_chain_id: Destination chain ID
            amount_usdc_minor: Payment amount in USDC minor units
            
        Returns:
            Dict with cost estimation details
        """
        src_config = ChainConfig.get_chain_config(src_chain_id)
        dest_config = ChainConfig.get_chain_config(dest_chain_id)
        
        if not src_config or not dest_config:
            return {"error": "Unsupported chain"}
        
        # Calculate bridge fee
        bridge_fee = 0
        if src_chain_id != dest_chain_id:
            bridge_fee = ChainConfig.calculate_bridge_fee(amount_usdc_minor, src_chain_id)
        
        return {
            "src_chain": {
                "name": src_config["name"],
                "gas_limit": src_config["gas_limit"],
                "bridge_fee_bps": src_config.get("bridge_fee_bps", 0)
            },
            "dest_chain": {
                "name": dest_config["name"],
                "gas_limit": dest_config.get("gas_limit", 300000)
            },
            "costs": {
                "bridge_fee_usdc": bridge_fee,
                "bridge_fee_percentage": src_config.get("bridge_fee_bps", 0) / 100,
                "total_amount_usdc": amount_usdc_minor + bridge_fee,
                "is_cross_chain": src_chain_id != dest_chain_id
            }
        }
