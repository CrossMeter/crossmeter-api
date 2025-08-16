"""
Smart contract interface definitions for PIaaS router contracts.
"""

from typing import Dict, Any, List, Optional
from enum import Enum
import struct
import hashlib
from dataclasses import dataclass


class FunctionSelector(str, Enum):
    """Smart contract function selectors (first 4 bytes of keccak256 hash)."""
    CREATE_PAYMENT = "0xa9059cbb"  # createPayment(address,uint256,uint32,uint32,bytes32)
    BRIDGE_PAYMENT = "0x23b872dd"  # bridgePayment(address,uint256,uint32,uint32,address,bytes32)
    BATCH_PAYMENT = "0x18160ddd"   # batchPayment(address[],uint256[],uint32,uint32,bytes32)


@dataclass
class ContractFunction:
    """Smart contract function definition."""
    name: str
    selector: str
    parameters: List[Dict[str, str]]
    description: str


class RouterContractABI:
    """Router contract ABI definitions and encoding utilities."""
    
    # Function definitions
    FUNCTIONS = {
        "createPayment": ContractFunction(
            name="createPayment",
            selector=FunctionSelector.CREATE_PAYMENT.value,
            parameters=[
                {"name": "recipient", "type": "address"},
                {"name": "amount", "type": "uint256"},
                {"name": "srcChainId", "type": "uint32"},
                {"name": "destChainId", "type": "uint32"},
                {"name": "paymentId", "type": "bytes32"}
            ],
            description="Create a cross-chain payment"
        ),
        "bridgePayment": ContractFunction(
            name="bridgePayment", 
            selector=FunctionSelector.BRIDGE_PAYMENT.value,
            parameters=[
                {"name": "recipient", "type": "address"},
                {"name": "amount", "type": "uint256"},
                {"name": "srcChainId", "type": "uint32"},
                {"name": "destChainId", "type": "uint32"},
                {"name": "bridgeAddress", "type": "address"},
                {"name": "paymentId", "type": "bytes32"}
            ],
            description="Create a bridged cross-chain payment with custom bridge"
        ),
        "batchPayment": ContractFunction(
            name="batchPayment",
            selector=FunctionSelector.BATCH_PAYMENT.value,
            parameters=[
                {"name": "recipients", "type": "address[]"},
                {"name": "amounts", "type": "uint256[]"},
                {"name": "srcChainId", "type": "uint32"},
                {"name": "destChainId", "type": "uint32"},
                {"name": "paymentId", "type": "bytes32"}
            ],
            description="Create multiple payments in a single transaction"
        )
    }
    
    @classmethod
    def encode_address(cls, address: str) -> str:
        """Encode Ethereum address to 32-byte hex."""
        if not address.startswith('0x'):
            address = '0x' + address
        # Remove 0x prefix and pad to 64 characters (32 bytes)
        return address[2:].lower().zfill(64)
    
    @classmethod
    def encode_uint256(cls, value: int) -> str:
        """Encode uint256 to 32-byte hex."""
        return f"{value:064x}"
    
    @classmethod
    def encode_uint32(cls, value: int) -> str:
        """Encode uint32 to 32-byte hex (padded)."""
        return f"{value:064x}"
    
    @classmethod
    def encode_bytes32(cls, value: str) -> str:
        """Encode string to bytes32 hex."""
        if value.startswith('0x'):
            value = value[2:]
        # If it's already 32 bytes (64 hex chars), return as is
        if len(value) == 64:
            return value.lower()
        # Otherwise, encode as UTF-8 and hash
        bytes_data = value.encode('utf-8')
        hash_obj = hashlib.sha256(bytes_data)
        return hash_obj.hexdigest()
    
    @classmethod
    def encode_address_array(cls, addresses: List[str]) -> str:
        """Encode array of addresses."""
        # Array encoding: offset(32) + length(32) + elements
        length = len(addresses)
        encoded = cls.encode_uint256(0x20)  # Offset to array data
        encoded += cls.encode_uint256(length)  # Array length
        
        for address in addresses:
            encoded += cls.encode_address(address)
        
        return encoded
    
    @classmethod
    def encode_uint256_array(cls, values: List[int]) -> str:
        """Encode array of uint256 values."""
        # Array encoding: offset(32) + length(32) + elements  
        length = len(values)
        encoded = cls.encode_uint256(0x20)  # Offset to array data
        encoded += cls.encode_uint256(length)  # Array length
        
        for value in values:
            encoded += cls.encode_uint256(value)
        
        return encoded


class ChainConfig:
    """Chain-specific configuration for router contracts."""
    
    CHAIN_CONFIGS = {
        1: {  # Ethereum Mainnet
            "name": "Ethereum",
            "router_address": "0x1234567890123456789012345678901234567890",
            "usdc_address": "0xA0b86a33E6C617Ad208c59E7c7f8C48e9b1b3B2c",
            "gas_limit": 300000,
            "bridge_fee_bps": 5  # 0.05%
        },
        8453: {  # Base Mainnet
            "name": "Base",
            "router_address": "0x2345678901234567890123456789012345678901", 
            "usdc_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "gas_limit": 250000,
            "bridge_fee_bps": 3  # 0.03%
        },
        84532: {  # Base Sepolia
            "name": "Base Sepolia",
            "router_address": "0x3456789012345678901234567890123456789012",
            "usdc_address": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
            "gas_limit": 250000,
            "bridge_fee_bps": 5  # 0.05%
        },
        10: {  # Optimism
            "name": "Optimism",
            "router_address": "0x4567890123456789012345678901234567890123",
            "usdc_address": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
            "gas_limit": 200000,
            "bridge_fee_bps": 4  # 0.04%
        },
        42161: {  # Arbitrum One
            "name": "Arbitrum",
            "router_address": "0x5678901234567890123456789012345678901234",
            "usdc_address": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
            "gas_limit": 180000,
            "bridge_fee_bps": 3  # 0.03%
        },
        137: {  # Polygon
            "name": "Polygon",
            "router_address": "0x6789012345678901234567890123456789012345",
            "usdc_address": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
            "gas_limit": 150000,
            "bridge_fee_bps": 6  # 0.06%
        }
    }
    
    @classmethod
    def get_chain_config(cls, chain_id: int) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific chain."""
        return cls.CHAIN_CONFIGS.get(chain_id)
    
    @classmethod
    def get_router_address(cls, chain_id: int) -> Optional[str]:
        """Get router contract address for a chain."""
        config = cls.get_chain_config(chain_id)
        return config.get("router_address") if config else None
    
    @classmethod
    def calculate_bridge_fee(cls, amount: int, src_chain_id: int) -> int:
        """Calculate bridge fee in minor units."""
        config = cls.get_chain_config(src_chain_id)
        if not config:
            return 0
        
        fee_bps = config.get("bridge_fee_bps", 5)
        return (amount * fee_bps) // 10000  # bps to percentage
    
    @classmethod
    def get_supported_chains(cls) -> List[int]:
        """Get list of supported chain IDs."""
        return list(cls.CHAIN_CONFIGS.keys())


class PaymentType(str, Enum):
    """Types of payments that can be processed."""
    SIMPLE = "simple"           # Direct payment, same chain
    BRIDGE = "bridge"           # Cross-chain payment via bridge
    BATCH = "batch"             # Multiple recipients
    SUBSCRIPTION = "subscription"  # Recurring payment


def select_optimal_function(
    src_chain_id: int,
    dest_chain_id: int,
    payment_type: PaymentType = PaymentType.SIMPLE,
    recipients_count: int = 1
) -> str:
    """
    Select the optimal contract function based on payment parameters.
    
    Args:
        src_chain_id: Source chain ID
        dest_chain_id: Destination chain ID  
        payment_type: Type of payment
        recipients_count: Number of recipients
        
    Returns:
        str: Function name to use
    """
    # Batch payments for multiple recipients
    if recipients_count > 1:
        return "batchPayment"
    
    # Bridge payment for cross-chain transfers
    if src_chain_id != dest_chain_id:
        return "bridgePayment"
    
    # Simple payment for same-chain transfers
    return "createPayment"
