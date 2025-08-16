from datetime import datetime
from typing import Dict, Any, Optional, List
from app.database.client import get_supabase_admin_client
from app.schemas.product import ProductCreate, ProductResponse, ProductType


class ProductService:
    """Service for managing product operations."""
    
    def __init__(self):
        self.supabase = get_supabase_admin_client()
    
    async def create_product(self, product_data: ProductCreate) -> ProductResponse:
        """Create a new product."""
        try:
            # Ensure vendor_id is provided
            if not product_data.vendor_id:
                raise ValueError("vendor_id is required")
                
            # Generate product ID
            product_id = f"p_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Verify vendor exists
            vendor_result = self.supabase.table("vendors").select("vendor_id").eq("vendor_id", product_data.vendor_id).execute()
            if not vendor_result.data:
                raise ValueError(f"Vendor {product_data.vendor_id} not found")
            
            # Prepare data for insertion
            insert_data = {
                "product_id": product_id,
                "vendor_id": product_data.vendor_id,
                "name": product_data.name,
                "description": product_data.description,
                "product_type": product_data.product_type.value,
                "default_amount_usdc_minor": product_data.default_amount_usdc_minor,
                "metadata": product_data.metadata or {},
            }
            
            # Insert into database
            result = self.supabase.table("products").insert(insert_data).execute()
            
            if not result.data:
                raise ValueError("Failed to create product")
            
            product_row = result.data[0]
            
            # Parse timestamps
            created_at = self._parse_timestamp(product_row["created_at"])
            updated_at = self._parse_timestamp(product_row["updated_at"])
            
            return ProductResponse(
                product_id=product_row["product_id"],
                vendor_id=product_row["vendor_id"],
                name=product_row["name"],
                description=product_row["description"],
                product_type=ProductType(product_row["product_type"]),
                default_amount_usdc_minor=product_row["default_amount_usdc_minor"],
                metadata=product_row["metadata"],
                created_at=created_at,
                updated_at=updated_at
            )
            
        except Exception as e:
            raise ValueError(f"Error creating product: {str(e)}")
    
    async def get_product(self, product_id: str) -> Optional[ProductResponse]:
        """Get product by ID."""
        try:
            result = self.supabase.table("products").select("*").eq("product_id", product_id).execute()
            
            if not result.data:
                return None
            
            product_row = result.data[0]
            
            # Parse timestamps
            created_at = self._parse_timestamp(product_row["created_at"])
            updated_at = self._parse_timestamp(product_row["updated_at"])
            
            return ProductResponse(
                product_id=product_row["product_id"],
                vendor_id=product_row["vendor_id"],
                name=product_row["name"],
                description=product_row["description"],
                product_type=ProductType(product_row["product_type"]),
                default_amount_usdc_minor=product_row["default_amount_usdc_minor"],
                metadata=product_row["metadata"],
                created_at=created_at,
                updated_at=updated_at
            )
            
        except Exception as e:
            raise ValueError(f"Error fetching product: {str(e)}")
    
    async def list_vendor_products(self, vendor_id: str) -> List[ProductResponse]:
        """List all products for a vendor."""
        try:
            result = self.supabase.table("products").select("*").eq("vendor_id", vendor_id).order("created_at", desc=True).execute()
            
            products = []
            for product_row in result.data:
                # Parse timestamps
                created_at = self._parse_timestamp(product_row["created_at"])
                updated_at = self._parse_timestamp(product_row["updated_at"])
                
                products.append(ProductResponse(
                    product_id=product_row["product_id"],
                    vendor_id=product_row["vendor_id"],
                    name=product_row["name"],
                    description=product_row["description"],
                    product_type=ProductType(product_row["product_type"]),
                    default_amount_usdc_minor=product_row["default_amount_usdc_minor"],
                    metadata=product_row["metadata"],
                    created_at=created_at,
                    updated_at=updated_at
                ))
            
            return products
            
        except Exception as e:
            raise ValueError(f"Error listing products: {str(e)}")
    
    async def update_product(self, product_id: str, update_data: Dict[str, Any]) -> Optional[ProductResponse]:
        """Update product by ID."""
        try:
            # Filter out None values
            filtered_data = {k: v for k, v in update_data.items() if v is not None}
            if not filtered_data:
                # If no updates, just return current product
                return await self.get_product(product_id)
            
            # Convert enum to string if present
            if "product_type" in filtered_data and isinstance(filtered_data["product_type"], ProductType):
                filtered_data["product_type"] = filtered_data["product_type"].value
            
            # Update in database
            result = self.supabase.table("products").update(filtered_data).eq("product_id", product_id).execute()
            
            if not result.data:
                return None
            
            product_row = result.data[0]
            
            # Parse timestamps
            created_at = self._parse_timestamp(product_row["created_at"])
            updated_at = self._parse_timestamp(product_row["updated_at"])
            
            return ProductResponse(
                product_id=product_row["product_id"],
                vendor_id=product_row["vendor_id"],
                name=product_row["name"],
                description=product_row["description"],
                product_type=ProductType(product_row["product_type"]),
                default_amount_usdc_minor=product_row["default_amount_usdc_minor"],
                metadata=product_row["metadata"],
                created_at=created_at,
                updated_at=updated_at
            )
            
        except Exception as e:
            raise ValueError(f"Error updating product: {str(e)}")
    
    async def delete_product(self, product_id: str) -> bool:
        """Delete product by ID."""
        try:
            # Check if product has any payment intents
            payment_result = self.supabase.table("payment_intents").select("id").eq("product_id", product_id).limit(1).execute()
            
            if payment_result.data:
                raise ValueError("Cannot delete product with existing payment intents")
            
            # Delete the product
            result = self.supabase.table("products").delete().eq("product_id", product_id).execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            raise ValueError(f"Error deleting product: {str(e)}")
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse Supabase timestamp with high precision."""
        if timestamp_str.endswith('Z'):
            timestamp_str = timestamp_str[:-1] + '+00:00'
        
        # Handle microseconds precision
        if '.' in timestamp_str:
            dt_part, rest = timestamp_str.split('.')
            if '+' in rest:
                micro_part, tz_part = rest.split('+')
                micro_part = micro_part[:6].ljust(6, '0')  # Ensure 6 digits
                timestamp_str = f"{dt_part}.{micro_part}+{tz_part}"
        
        return datetime.fromisoformat(timestamp_str)
