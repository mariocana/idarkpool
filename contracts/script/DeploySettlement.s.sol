// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/DarkPoolSettlement.sol";

contract DeploySettlement is Script {
    function run() external {
        address enclaveSigner = vm.envAddress("ENCLAVE_SIGNER");

        vm.startBroadcast();
        DarkPoolSettlement s = new DarkPoolSettlement(enclaveSigner);
        console.log("Deployed DarkPoolSettlement at:", address(s));
        vm.stopBroadcast();
    }
}
