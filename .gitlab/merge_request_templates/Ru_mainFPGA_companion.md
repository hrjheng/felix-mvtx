<!---
Please read this!

This template is intended to be used for a merge request in this branch associated to RU_mainFPGA merge request

The suggested title of the MR is the same as the original merge request.

If you have software modifications which need to be done in this MR, please port the subtree following the procedure indicataed in RU_mainFPGA/doc/Subtree.md
--->

Companion MR of RU_mainFPGA!<MR_NUMBER>

Checklist for the MR creator:

- [ ] Port board support software (if needed, in case add ~Software)
- [ ] Run the deployment test from RU_mainFPGA
- [ ] Run the pre_merge test from RU_mainFPGA: it will copy the bitfile in the correct folder and update the deployment_test yml files
- [ ] After the MR is automatically updated by `itsruci` bot, run it from CRU_ITS to verify that the paths are indicated correctly

/label ~"Done - await review" ~Configuration
/assign @mlupi @avelure
