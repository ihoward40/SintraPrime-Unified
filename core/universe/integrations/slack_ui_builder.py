"""
Slack UI Builder Module

Provides Block Kit utilities and interactive component factories for rich Slack messages.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


class SlackUIBuilder:
    """Factory for building Slack Block Kit messages and interactive components."""

    # Block types
    SECTION = "section"
    DIVIDER = "divider"
    IMAGE = "image"
    ACTIONS = "actions"
    BUTTON = "button"
    CONTEXT = "context"
    HEADER = "header"
    RICH_TEXT = "rich_text"

    @staticmethod
    def create_button(
        text: str,
        action_id: str,
        value: str = None,
        style: str = None,
        confirm: Dict = None,
    ) -> Dict:
        """
        Create an interactive button element.

        Args:
            text: Button display text
            action_id: Unique identifier for the button action
            value: Value to send when clicked
            style: 'primary' or 'danger'
            confirm: Optional confirmation dialog

        Returns:
            Button element dictionary
        """
        button = {
            "type": "button",
            "text": {"type": "plain_text", "text": text, "emoji": True},
            "action_id": action_id,
        }

        if value:
            button["value"] = value

        if style in ["primary", "danger"]:
            button["style"] = style

        if confirm:
            button["confirm"] = confirm

        return button

    @staticmethod
    def create_confirmation_dialog(
        title: str, text: str, confirm_text: str = "Confirm", deny_text: str = "Cancel"
    ) -> Dict:
        """
        Create a confirmation dialog.

        Args:
            title: Dialog title
            text: Dialog text
            confirm_text: Confirmation button text
            deny_text: Denial button text

        Returns:
            Confirmation dialog dictionary
        """
        return {
            "title": {"type": "plain_text", "text": title},
            "text": {"type": "mrkdwn", "text": text},
            "confirm": {"type": "plain_text", "text": confirm_text},
            "deny": {"type": "plain_text", "text": deny_text},
        }

    @staticmethod
    def create_section_block(
        text: str = None,
        markdown: bool = True,
        block_id: str = None,
        accessory: Dict = None,
        fields: List[Dict] = None,
    ) -> Dict:
        """
        Create a section block.

        Args:
            text: Section text content
            markdown: Whether to use markdown formatting
            block_id: Optional block identifier
            accessory: Optional accessory element (button, image, etc.)
            fields: Optional list of field elements

        Returns:
            Section block dictionary
        """
        block = {"type": "section"}

        if block_id:
            block["block_id"] = block_id

        if text:
            text_type = "mrkdwn" if markdown else "plain_text"
            block["text"] = {"type": text_type, "text": text}

        if fields:
            block["fields"] = fields

        if accessory:
            block["accessory"] = accessory

        return block

    @staticmethod
    def create_header_block(text: str, block_id: str = None) -> Dict:
        """
        Create a header block.

        Args:
            text: Header text
            block_id: Optional block identifier

        Returns:
            Header block dictionary
        """
        block = {
            "type": "header",
            "text": {"type": "plain_text", "text": text, "emoji": True},
        }

        if block_id:
            block["block_id"] = block_id

        return block

    @staticmethod
    def create_divider_block(block_id: str = None) -> Dict:
        """
        Create a divider block.

        Args:
            block_id: Optional block identifier

        Returns:
            Divider block dictionary
        """
        block = {"type": "divider"}

        if block_id:
            block["block_id"] = block_id

        return block

    @staticmethod
    def create_context_block(
        elements: List[Union[str, Dict]], block_id: str = None
    ) -> Dict:
        """
        Create a context block for supplementary information.

        Args:
            elements: List of text or image elements
            block_id: Optional block identifier

        Returns:
            Context block dictionary
        """
        block = {"type": "context", "elements": []}

        for element in elements:
            if isinstance(element, str):
                block["elements"].append({"type": "mrkdwn", "text": element})
            elif isinstance(element, dict):
                block["elements"].append(element)

        if block_id:
            block["block_id"] = block_id

        return block

    @staticmethod
    def create_actions_block(elements: List[Dict], block_id: str = None) -> Dict:
        """
        Create an actions block with interactive elements.

        Args:
            elements: List of button or select elements
            block_id: Optional block identifier

        Returns:
            Actions block dictionary
        """
        block = {"type": "actions", "elements": elements}

        if block_id:
            block["block_id"] = block_id

        return block

    @staticmethod
    def create_status_message(
        title: str, status: str, details: str = None, timestamp: bool = True
    ) -> Dict:
        """
        Create a status message with progress indicator.

        Args:
            title: Message title
            status: Status text ('pending', 'running', 'success', 'error')
            details: Optional detailed information
            timestamp: Whether to include timestamp

        Returns:
            Message payload dictionary
        """
        status_emoji = {
            "pending": "⏳",
            "running": "🔄",
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
        }

        emoji = status_emoji.get(status, "•")
        status_text = f"{emoji} {status.upper()}"

        blocks = [
            SlackUIBuilder.create_header_block(f"{emoji} {title}"),
            SlackUIBuilder.create_section_block(status_text),
        ]

        if details:
            blocks.append(SlackUIBuilder.create_context_block([details]))

        if timestamp:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            blocks.append(SlackUIBuilder.create_context_block([f"_Updated: {now}_"]))

        return {"blocks": blocks}

    @staticmethod
    def create_task_result_message(
        task_name: str, success: bool, result: str = None, error: str = None
    ) -> Dict:
        """
        Create a formatted task result message.

        Args:
            task_name: Name of the task
            success: Whether task succeeded
            result: Task result/output
            error: Error message if failed

        Returns:
            Message payload dictionary
        """
        status = "success" if success else "error"
        status_emoji = "✅" if success else "❌"

        blocks = [
            SlackUIBuilder.create_header_block(f"{status_emoji} Task: {task_name}"),
            SlackUIBuilder.create_section_block(f"*Status:* {status.upper()}"),
        ]

        if result:
            blocks.append(
                SlackUIBuilder.create_section_block(f"*Result:*\n```{result}```")
            )

        if error:
            blocks.append(
                SlackUIBuilder.create_section_block(f"*Error:*\n```{error}```", markdown=True)
            )

        blocks.append(SlackUIBuilder.create_divider_block())
        blocks.append(
            SlackUIBuilder.create_context_block(
                [f"Completed at {datetime.now().strftime('%H:%M:%S')}"]
            )
        )

        return {"blocks": blocks}

    @staticmethod
    def create_error_dialog(title: str, message: str, details: str = None) -> Dict:
        """
        Create an error dialog modal.

        Args:
            title: Dialog title
            message: Error message
            details: Optional detailed error information

        Returns:
            Modal payload dictionary
        """
        blocks = [
            SlackUIBuilder.create_header_block(f"❌ {title}"),
            SlackUIBuilder.create_section_block(message),
        ]

        if details:
            blocks.append(SlackUIBuilder.create_section_block(f"```{details}```"))

        return {
            "type": "modal",
            "callback_id": "error_dialog",
            "title": {"type": "plain_text", "text": title},
            "blocks": blocks,
            "close": {"type": "plain_text", "text": "Close"},
        }

    @staticmethod
    def create_select_menu(
        action_id: str,
        placeholder: str,
        options: List[Dict],
        block_id: str = None,
    ) -> Dict:
        """
        Create a select menu element.

        Args:
            action_id: Unique identifier for the menu
            placeholder: Placeholder text
            options: List of option dictionaries with 'text' and 'value'
            block_id: Optional block identifier

        Returns:
            Select menu block dictionary
        """
        menu = {
            "type": "static_select",
            "action_id": action_id,
            "placeholder": {"type": "plain_text", "text": placeholder},
            "options": [
                {"text": {"type": "plain_text", "text": opt["text"]}, "value": opt["value"]}
                for opt in options
            ],
        }

        if block_id:
            menu["block_id"] = block_id

        return menu

    @staticmethod
    def create_attachment(
        fallback: str,
        color: str = None,
        title: str = None,
        text: str = None,
        fields: List[Dict] = None,
    ) -> Dict:
        """
        Create a legacy message attachment (for compatibility).

        Args:
            fallback: Fallback text for clients without formatting support
            color: Color code (hex or color name)
            title: Attachment title
            text: Attachment text
            fields: List of field dictionaries

        Returns:
            Attachment dictionary
        """
        attachment = {"fallback": fallback}

        if color:
            attachment["color"] = color

        if title:
            attachment["title"] = title

        if text:
            attachment["text"] = text

        if fields:
            attachment["fields"] = fields

        return attachment

    @staticmethod
    def validate_blocks(blocks: List[Dict]) -> bool:
        """
        Validate block structure (basic validation).

        Args:
            blocks: List of block dictionaries

        Returns:
            True if blocks are valid, False otherwise
        """
        if not isinstance(blocks, list):
            return False

        valid_types = {
            "section",
            "divider",
            "image",
            "actions",
            "context",
            "header",
            "rich_text",
            "input",
        }

        for block in blocks:
            if not isinstance(block, dict):
                return False

            if block.get("type") not in valid_types:
                return False

        return True

    @staticmethod
    def serialize_message(blocks: List[Dict], attachments: List[Dict] = None) -> str:
        """
        Serialize blocks and attachments to JSON.

        Args:
            blocks: List of block dictionaries
            attachments: Optional list of attachment dictionaries

        Returns:
            JSON string representation
        """
        message = {"blocks": blocks}

        if attachments:
            message["attachments"] = attachments

        return json.dumps(message)
