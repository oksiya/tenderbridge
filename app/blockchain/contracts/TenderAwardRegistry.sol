// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract TenderAwardRegistry {
    struct Award {
        string tenderId;
        string winningBidId;
        string winningCompanyId;
        uint256 awardAmount;
        uint256 awardDate;
        address awardedBy;
        string dataHash;
        bool exists;
    }
    
    mapping(string => Award) private awards;
    string[] private awardIds;
    
    event TenderAwarded(
        string indexed tenderId,
        string winningBidId,
        string winningCompanyId,
        uint256 awardAmount,
        uint256 awardDate,
        address awardedBy,
        string dataHash
    );
    
    function recordAward(
        string memory _tenderId,
        string memory _winningBidId,
        string memory _winningCompanyId,
        uint256 _awardAmount,
        string memory _dataHash
    ) public {
        require(!awards[_tenderId].exists, "Award already recorded");
        
        awards[_tenderId] = Award({
            tenderId: _tenderId,
            winningBidId: _winningBidId,
            winningCompanyId: _winningCompanyId,
            awardAmount: _awardAmount,
            awardDate: block.timestamp,
            awardedBy: msg.sender,
            dataHash: _dataHash,
            exists: true
        });
        
        awardIds.push(_tenderId);
        
        emit TenderAwarded(
            _tenderId,
            _winningBidId,
            _winningCompanyId,
            _awardAmount,
            block.timestamp,
            msg.sender,
            _dataHash
        );
    }
    
    function getAward(string memory _tenderId) 
        public 
        view 
        returns (
            string memory tenderId,
            string memory winningBidId,
            string memory winningCompanyId,
            uint256 awardAmount,
            uint256 awardDate,
            address awardedBy,
            string memory dataHash
        ) 
    {
        require(awards[_tenderId].exists, "Award not found");
        Award memory award = awards[_tenderId];
        return (
            award.tenderId,
            award.winningBidId,
            award.winningCompanyId,
            award.awardAmount,
            award.awardDate,
            award.awardedBy,
            award.dataHash
        );
    }
    
    function verifyAward(string memory _tenderId, string memory _dataHash) 
        public 
        view 
        returns (bool) 
    {
        if (!awards[_tenderId].exists) return false;
        return keccak256(bytes(awards[_tenderId].dataHash)) == keccak256(bytes(_dataHash));
    }
    
    function getAwardCount() public view returns (uint256) {
        return awardIds.length;
    }
}
