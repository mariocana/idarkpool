// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import { IERC20 } from "openzeppelin-contracts/contracts/token/ERC20/IERC20.sol";
import { SafeERC20 } from "openzeppelin-contracts/contracts/token/ERC20/utils/SafeERC20.sol";
import { Ownable } from "openzeppelin-contracts/contracts/access/Ownable.sol";
import {ECDSA} from "openzeppelin-contracts/contracts/utils/cryptography/ECDSA.sol";


contract DarkPoolSettlement is Ownable {
    using SafeERC20 for IERC20;
    using ECDSA for bytes32;

    struct Trade {
        address maker;
        address taker;
        address tokenA;
        address tokenB;
        uint256 amountA;
        uint256 amountB;
        uint256 nonce;
        uint256 deadline;
    }

    mapping(bytes32 => bool) public executed;
    address public enclaveSigner;

    event Settled(address indexed maker, address indexed taker, uint256 amountA, uint256 amountB);

    constructor(address _enclaveSigner) Ownable(msg.sender) {
        enclaveSigner = _enclaveSigner;
    }

    function setEnclaveSigner(address newSigner) external onlyOwner {
        enclaveSigner = newSigner;
    }

    function settle(Trade calldata t, bytes calldata signature) external {
        require(t.tokenA != address(0) && t.tokenB != address(0), "Invalid token");
        require(block.timestamp <= t.deadline, "Expired");
        bytes32 hash = _hashTrade(t);
        require(!executed[hash], "Already executed");

        bytes32 ethSigned = keccak256(
            abi.encodePacked("\x19Ethereum Signed Message:\n32", hash)
        );
        address recovered = ECDSA.recover(ethSigned, signature);
        require(recovered == enclaveSigner, "Invalid signature");

        executed[hash] = true;

        IERC20(t.tokenA).safeTransferFrom(t.maker, t.taker, t.amountA);
        IERC20(t.tokenB).safeTransferFrom(t.taker, t.maker, t.amountB);

        emit Settled(t.maker, t.taker, t.amountA, t.amountB);
    }

    function _hashTrade(Trade memory t) internal pure returns (bytes32) {
        return keccak256(
            abi.encode(
                t.maker,
                t.taker,
                t.tokenA,
                t.tokenB,
                t.amountA,
                t.amountB,
                t.nonce,
                t.deadline
            )
        );
    }
}